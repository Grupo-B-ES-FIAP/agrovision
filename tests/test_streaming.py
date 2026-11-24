#Testes do streaming: seguranca dos eventos, consumidor e fluxo completo

import json

import pytest

from agrovision.streaming import eventos, produtor, transporte
from agrovision.streaming.consumidor import Consumidor
from agrovision.streaming.eventos import ANALISE, SENSOR, EventoInvalido
from agrovision.streaming.transporte import TransporteMemoria

SENSOR_OK = {"umidade_solo": 50.0, "temperatura": 25.0}
ANALISE_OK = {"nome_imagem": "f.jpg", "categoria": "Doente", "acuracia": 90.0, "data": "2026-09-01"}


def codigo(evento, **kwargs) -> str:
    with pytest.raises(EventoInvalido) as erro:
        eventos.validar(evento, **kwargs)
    return erro.value.codigo


def test_evento_integro_e_aceito():
    evento = eventos.criar(SENSOR, "Talhão A", SENSOR_OK)
    assert eventos.validar(evento) is evento


def test_carga_adulterada_quebra_a_assinatura():
    evento = eventos.criar(SENSOR, "Talhão A", SENSOR_OK)
    evento["carga"]["umidade_solo"] = 99.0
    assert codigo(evento) == "assinatura"


def test_chave_errada_quebra_a_assinatura():
    evento = eventos.criar(SENSOR, "Talhão A", SENSOR_OK, chave="outra-chave")
    assert codigo(evento) == "assinatura"


def test_dispositivo_fora_da_lista_e_rejeitado():
    evento = eventos.criar(SENSOR, "Talhão A", SENSOR_OK, dispositivo="sensor-clone-99")
    assert codigo(evento) == "dispositivo"


def test_evento_antigo_e_rejeitado_como_replay():
    evento = eventos.criar(SENSOR, "Talhão A", SENSOR_OK, ts=1000.0)
    assert codigo(evento, agora=1000.0 + eventos.JANELA_SEGUNDOS + 1) == "expirado"


@pytest.mark.parametrize("carga", [
    {"umidade_solo": 250.0, "temperatura": 25.0},
    {"umidade_solo": "alta", "temperatura": 25.0},
    {"umidade_solo": 50.0},
])
def test_sensor_fora_da_faixa_ou_incompleto(carga):
    assert codigo(eventos.criar(SENSOR, "Talhão A", carga)) == "esquema"


def test_analise_com_categoria_ou_data_invalida():
    assert codigo(eventos.criar(ANALISE, "Talhão A", {**ANALISE_OK, "categoria": "Morta"})) \
        == "esquema"
    assert codigo(eventos.criar(ANALISE, "Talhão A", {**ANALISE_OK, "data": "01/09"})) == "esquema"


def test_lixo_nao_derruba_o_validador():
    assert codigo(None) == "esquema"
    assert codigo({"id": "x"}) == "esquema"


@pytest.fixture
def consumidor(camadas):
    return Consumidor(TransporteMemoria(), lote_analises=2)


def test_replay_do_mesmo_id_e_rejeitado(consumidor):
    evento = eventos.criar(SENSOR, "Talhão A", SENSOR_OK)
    assert consumidor.tratar(evento) is True
    assert consumidor.tratar(dict(evento)) is False
    assert consumidor.motivos["repetido"] == 1


def test_rejeitado_vai_para_o_topico_de_rejeitados(consumidor):
    consumidor.tratar({"lixo": True})
    assert len(consumidor.transporte.filas[eventos.TOPICO_REJEITADOS]) == 1


def test_umidade_baixa_alerta_uma_vez_e_de_novo_so_apos_recuperar(consumidor):
    def leitura(umidade):
        consumidor.tratar(eventos.criar(SENSOR, "Talhão B", {**SENSOR_OK, "umidade_solo": umidade}))

    leitura(20.0)
    leitura(18.0)
    assert consumidor.contagem["alertas"] == 1
    leitura(60.0)
    leitura(20.0)
    assert consumidor.contagem["alertas"] == 2


def test_analises_chegam_na_bronze_e_disparam_as_regras(consumidor, camadas):
    # 5 doentes de 6 no mesmo talhao e dia: acima do limiar critico de 30%.
    for i in range(6):
        categoria = "Doente" if i < 5 else "Saudável"
        carga = {**ANALISE_OK, "nome_imagem": f"f{i}.jpg", "categoria": categoria}
        consumidor.tratar(eventos.criar(ANALISE, "Talhão B", carga))
    consumidor.encerrar()

    assert len(camadas.ler_camada(camadas.BRONZE)) == 6
    assert camadas.ALERTAS.exists()
    alertas = list(consumidor.alertas)
    assert alertas and alertas[0]["origem"] == "analise" and alertas[0]["talhao"] == "Talhão B"
    assert json.loads((camadas.SAIDA / "streaming_estado.json").read_text(encoding="utf-8"))


def test_simulador_e_deterministico():
    primeiro = [e["carga"] for _, e in produtor.Simulador(semente=7).proximo()]
    segundo = [e["carga"] for _, e in produtor.Simulador(semente=7).proximo()]
    assert primeiro == segundo


def test_fluxo_completo_aceita_o_normal_e_rejeita_todos_os_ataques(consumidor):
    transporte = consumidor.transporte
    simulador = produtor.Simulador()
    produtor.executar(transporte, 3, simulador=simulador, aviso=lambda *_: None)
    for tipo in produtor.ATAQUES:
        topico, evento = simulador.ataque(tipo)
        transporte.publicar(topico, evento)

    consumidor.ciclo(espera=0)

    assert consumidor.contagem["aceitos"] == 27
    assert consumidor.contagem["rejeitados"] == len(produtor.ATAQUES)
    assert set(consumidor.motivos) == {"assinatura", "repetido", "dispositivo", "esquema"}


def test_demo_roda_sem_broker_e_grava_o_estado(camadas):
    from agrovision.streaming import demo

    consumidor = demo.executar(ticks=8, ataque_a_cada=4)

    assert consumidor.contagem["rejeitados"] == 2
    estado = camadas.SAIDA / "demonstracao" / "streaming_estado.json"
    assert json.loads(estado.read_text(encoding="utf-8"))["contagem"]["aceitos"] == 72


def test_broker_ativo_e_falso_para_porta_fechada():
    assert transporte.broker_ativo("localhost:1", espera=0.2) is False
    assert transporte.broker_ativo("endereco-invalido", espera=0.2) is False
