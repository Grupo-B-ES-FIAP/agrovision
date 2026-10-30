"""Testes da ingestao: deteccao de arquivos novos, checkpoint e disparo da automacao."""

import importlib.util
import json
from pathlib import Path

import pytest
from conftest import registro

from agrovision import ingestao
from agrovision.exportacao import escrever_csv, gerar_json


def lote(localidade, data, doentes, total=10):
    return [
        registro(
            nome=f"{localidade}_{data}_{i}.jpg",
            categoria="Doente" if i < doentes else "Saudável",
            data=data,
            localidade=localidade,
        )
        for i in range(total)
    ]


@pytest.fixture
def entrada(tmp_path):
    pasta = tmp_path / "entrada"
    pasta.mkdir()
    return pasta


@pytest.fixture
def execucoes(camadas, monkeypatch):
    """Conta quantas vezes o pipeline (e com ele a automacao) foi acionado."""
    chamadas = []
    original = camadas.executar

    def contar():
        chamadas.append(1)
        return original()

    monkeypatch.setattr(camadas, "executar", contar)
    return chamadas


def test_arquivo_novo_entra_e_dispara_as_regras(camadas, entrada, execucoes):
    escrever_csv(entrada / "lote_1.csv", lote("Talhão A", "2026-09-10", 5))

    resumo = ingestao.processar(entrada)

    assert resumo["novos"] == 10
    assert len(camadas.ler_camada(camadas.BRONZE)) == 10
    assert [a["regra"] for a in resumo["alertas"]] == ["R3"]
    assert json.loads(camadas.ALERTAS.read_text(encoding="utf-8"))["alertas"][0]["regra"] == "R3"
    assert len(execucoes) == 1


def test_arquivo_ja_processado_nao_dispara_de_novo(camadas, entrada, execucoes):
    escrever_csv(entrada / "lote_1.csv", lote("Talhão A", "2026-09-10", 5))
    ingestao.processar(entrada)
    relatorios = list((camadas.SAIDA / "relatorios").glob("*.md"))

    resumo = ingestao.processar(entrada)

    assert resumo["arquivos"] == []
    assert resumo["novos"] == 0
    assert len(execucoes) == 1
    assert list((camadas.SAIDA / "relatorios").glob("*.md")) == relatorios
    assert len(camadas.ler_camada(camadas.BRONZE)) == 10


def test_arquivo_reenviado_com_outro_nome_nao_dispara(camadas, entrada, execucoes):
    registros = lote("Talhão A", "2026-09-10", 5)
    escrever_csv(entrada / "lote_1.csv", registros)
    ingestao.processar(entrada)

    escrever_csv(entrada / "lote_1_reenvio.csv", registros)
    resumo = ingestao.processar(entrada)

    assert resumo["novos"] == 0
    assert resumo["repetidos"] == 10
    assert resumo["alertas"] == []
    assert len(execucoes) == 1
    assert len(camadas.ler_camada(camadas.BRONZE)) == 10


def test_arquivo_que_cresce_entrega_so_o_que_e_novo(camadas, entrada, execucoes):
    velhos = lote("Talhão A", "2026-09-10", 1)
    escrever_csv(entrada / "lote.csv", velhos)
    ingestao.processar(entrada)

    escrever_csv(entrada / "lote.csv", velhos + lote("Talhão A", "2026-09-11", 1))
    resumo = ingestao.processar(entrada)

    assert resumo["novos"] == 10
    assert resumo["repetidos"] == 10
    assert len(camadas.ler_camada(camadas.BRONZE)) == 20
    assert len(execucoes) == 2


def test_tres_dias_seguidos_acionam_a_persistencia(camadas, entrada):
    for dia in ("2026-09-10", "2026-09-11", "2026-09-12"):
        escrever_csv(entrada / f"lote_{dia}.csv", lote("Talhão A", dia, 1))
        resumo = ingestao.processar(entrada)

    assert [(a["data"], a["regra"]) for a in resumo["alertas"]] == [("2026-09-12", "R4")]


def test_aceita_json_em_lista_e_no_formato_da_exportacao(camadas, entrada):
    registros = lote("Talhão A", "2026-09-10", 0, total=2)
    (entrada / "a.json").write_text(json.dumps(registros), encoding="utf-8")
    (entrada / "b.json").write_text(
        gerar_json(lote("Talhão B", "2026-09-10", 0, total=3)), encoding="utf-8"
    )

    resumo = ingestao.processar(entrada)

    assert resumo["novos"] == 5


def test_arquivo_sem_colunas_obrigatorias_e_rejeitado_uma_vez(camadas, entrada, execucoes):
    (entrada / "ruim.csv").write_text("a;b\n1;2\n", encoding="utf-8")

    primeiro = ingestao.processar(entrada)
    segundo = ingestao.processar(entrada)

    assert primeiro["arquivos"] == [{"arquivo": "ruim.csv", "status": "rejeitado"}]
    assert segundo["arquivos"] == []
    assert not execucoes
    assert ingestao.ler_checkpoint()["arquivos"]["ruim.csv"]["status"] == "rejeitado"


def test_json_invalido_e_rejeitado_e_o_proximo_arquivo_segue(camadas, entrada):
    (entrada / "a_quebrado.json").write_text("{nao e json", encoding="utf-8")
    escrever_csv(entrada / "b.csv", lote("Talhão A", "2026-09-10", 0, total=2))

    resumo = ingestao.processar(entrada)

    assert [a["status"] for a in resumo["arquivos"]] == ["rejeitado", "processado"]
    assert resumo["novos"] == 2


def test_ignora_temporarios_subpastas_e_outras_extensoes(camadas, entrada):
    escrever_csv(entrada / "lote.tmp", lote("Talhão A", "2026-09-10", 0, total=2))
    (entrada / "leia-me.txt").write_text("nada", encoding="utf-8")
    (entrada / "demonstracao").mkdir()
    escrever_csv(entrada / "demonstracao" / "lote.csv", lote("Talhão A", "2026-09-10", 0))

    assert ingestao.processar(entrada)["arquivos"] == []


def test_pasta_inexistente_nao_e_erro(camadas, tmp_path):
    assert ingestao.processar(tmp_path / "nao_existe")["novos"] == 0


def test_checkpoint_perdido_nao_duplica_a_bronze(camadas, entrada):
    escrever_csv(entrada / "lote.csv", lote("Talhão A", "2026-09-10", 1, total=4))
    ingestao.processar(entrada)
    camadas.CHECKPOINT.unlink()

    resumo = ingestao.processar(entrada)

    assert resumo["novos"] == 0
    assert len(camadas.ler_camada(camadas.BRONZE)) == 4


def test_limpar_apaga_o_checkpoint_e_o_arquivo_volta_a_entrar(camadas, entrada):
    escrever_csv(entrada / "lote.csv", lote("Talhão A", "2026-09-10", 1, total=4))
    ingestao.processar(entrada)

    camadas.limpar()
    resumo = ingestao.processar(entrada)

    assert not camadas.ler_camada(camadas.SILVER).empty
    assert resumo["novos"] == 4


def test_monitorar_pega_o_arquivo_que_chega_entre_os_ciclos(camadas, entrada, monkeypatch):
    def chegada(_segundos):
        escrever_csv(entrada / "lote.csv", lote("Talhão A", "2026-09-10", 0, total=3))

    monkeypatch.setattr(ingestao.time, "sleep", chegada)

    ingestao.monitorar(entrada, intervalo=1, ciclos=2)

    assert len(camadas.ler_camada(camadas.BRONZE)) == 3


def test_em_saida_redireciona_e_restaura(camadas, tmp_path):
    original = camadas.BRONZE
    outra = tmp_path / "outra"

    with camadas.em_saida(outra):
        dentro = (camadas.BRONZE, camadas.CHECKPOINT)

    assert dentro == (outra / original.name, outra / "checkpoint.json")
    assert camadas.BRONZE is original


def test_linha_de_comando_com_demonstracao_nao_toca_a_base_real(camadas, entrada, capsys):
    escrever_csv(entrada / "lote.csv", lote("Talhão A", "2026-09-10", 5))

    ingestao.main(["--demo", "--uma-vez", "--pasta", str(entrada)])

    saida = capsys.readouterr().out
    assert "ALERTA Talhão A" in saida
    assert (camadas.SAIDA / "demonstracao" / "checkpoint.json").exists()
    assert not camadas.BRONZE.exists()
    assert not camadas.CHECKPOINT.exists()


def carregar_gerador():
    caminho = Path(__file__).resolve().parents[1] / "scripts" / "gerar_lotes.py"
    especificacao = importlib.util.spec_from_file_location("gerar_lotes", caminho)
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


def test_gerador_continua_do_dia_seguinte_e_reenvia(entrada, capsys):
    gerador = carregar_gerador()

    gerador.main(["--destino", str(entrada), "--lotes", "2"])
    gerador.main(["--destino", str(entrada)])
    gerador.main(["--destino", str(entrada), "--reenviar"])

    nomes = sorted(arquivo.name for arquivo in entrada.iterdir())
    assert nomes == [
        "lote_2026-09-01.csv",
        "lote_2026-09-02.csv",
        "lote_2026-09-03.csv",
        "lote_2026-09-03_reenvio.csv",
    ]


def test_uma_vez_sem_novidade_informa_o_checkpoint(camadas, entrada, capsys):
    escrever_csv(entrada / "lote.csv", lote("Talhão A", "2026-09-10", 0))
    ingestao.main(["--uma-vez", "--pasta", str(entrada)])
    capsys.readouterr()

    ingestao.main(["--uma-vez", "--pasta", str(entrada)])

    assert "Nenhum arquivo novo. 1 arquivo(s) ja constam no checkpoint" in capsys.readouterr().out


def test_reiniciar_esvazia_a_pasta_de_dados(entrada):
    gerador = carregar_gerador()
    gerador.main(["--destino", str(entrada), "--lotes", "2"])
    (entrada / "ruim.csv").write_text("a;b", encoding="utf-8")
    (entrada / "leia-me.txt").write_text("fica", encoding="utf-8")

    gerador.main(["--destino", str(entrada), "--reiniciar"])

    assert [arquivo.name for arquivo in entrada.iterdir()] == ["leia-me.txt"]
