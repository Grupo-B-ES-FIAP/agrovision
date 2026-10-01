"""Testes do pipeline ETL: validacao, deduplicacao e indicadores."""

import json

from conftest import registro


def test_bronze_aceita_e_acumula(camadas):
    camadas.acrescentar_bronze([registro(nome="a.jpg")])
    total = camadas.acrescentar_bronze([registro(nome="b.jpg")])

    assert total == 2
    assert len(camadas.ler_camada(camadas.BRONZE)) == 2


def test_silver_descarta_data_invalida(camadas):
    camadas.acrescentar_bronze(
        [registro(nome="boa.jpg"), registro(nome="ruim.jpg", data="ontem")]
    )
    camadas.executar()
    silver = camadas.ler_camada(camadas.SILVER)

    assert list(silver["nome_imagem"]) == ["boa.jpg"]


def test_silver_descarta_confianca_nao_numerica(camadas):
    camadas.acrescentar_bronze(
        [registro(nome="boa.jpg"), registro(nome="ruim.jpg", acuracia="muito alta")]
    )
    camadas.executar()

    assert list(camadas.ler_camada(camadas.SILVER)["nome_imagem"]) == ["boa.jpg"]


def test_silver_descarta_categoria_fora_do_contrato(camadas):
    camadas.acrescentar_bronze(
        [registro(nome="boa.jpg"), registro(nome="ruim.jpg", categoria="Talvez doente")]
    )
    camadas.executar()

    assert list(camadas.ler_camada(camadas.SILVER)["nome_imagem"]) == ["boa.jpg"]


def test_silver_deduplica_mesma_imagem_data_e_local(camadas):
    camadas.acrescentar_bronze([registro(), registro()])
    camadas.executar()

    assert len(camadas.ler_camada(camadas.SILVER)) == 1


def test_mesma_imagem_em_outra_data_conta_duas_vezes(camadas):
    """A mesma folha fotografada em outro dia e uma analise nova."""
    camadas.acrescentar_bronze(
        [registro(data="2026-09-10"), registro(data="2026-09-20")]
    )
    camadas.executar()

    assert len(camadas.ler_camada(camadas.SILVER)) == 2


def test_mesma_imagem_em_outro_talhao_conta_duas_vezes(camadas):
    camadas.acrescentar_bronze(
        [registro(localidade="Talhão A"), registro(localidade="Talhão B")]
    )
    camadas.executar()

    assert len(camadas.ler_camada(camadas.SILVER)) == 2


def test_indicadores_do_gold(camadas):
    camadas.acrescentar_bronze(
        [
            registro(nome="s1.jpg", categoria="Saudável", acuracia=90.0),
            registro(nome="s2.jpg", categoria="Saudável", acuracia=100.0),
            registro(nome="d1.jpg", categoria="Doente", acuracia=80.0),
            registro(nome="d2.jpg", categoria="Doente", acuracia=90.0),
        ]
    )
    indicadores = camadas.executar()

    assert indicadores["total_imagens"] == 4
    assert indicadores["percentual_saudaveis"] == 50.0
    assert indicadores["percentual_doentes"] == 50.0
    assert indicadores["confianca_media"] == 90.0


def test_percentuais_somam_cem(camadas):
    camadas.acrescentar_bronze(
        [registro(nome=f"f{i}.jpg", categoria="Doente" if i < 2 else "Saudável") for i in range(7)]
    )
    indicadores = camadas.executar()
    soma = indicadores["percentual_saudaveis"] + indicadores["percentual_doentes"]

    assert abs(soma - 100.0) < 0.05


def test_gold_tem_contagem_por_localidade_e_por_dia(camadas):
    camadas.acrescentar_bronze(
        [
            registro(nome="a.jpg", localidade="Talhão A", data="2026-09-10"),
            registro(nome="b.jpg", localidade="Talhão B", data="2026-09-11", categoria="Doente"),
        ]
    )
    indicadores = camadas.executar()

    assert set(indicadores["por_localidade"]) == {"Talhão A", "Talhão B"}
    assert set(indicadores["tendencia_diaria"]) == {"2026-09-10", "2026-09-11"}


def test_base_vazia_gera_gold_valido(camadas):
    indicadores = camadas.executar()

    assert indicadores["total_imagens"] == 0
    assert json.loads(camadas.GOLD.read_text(encoding="utf-8"))["total_imagens"] == 0


def test_garantir_nao_reprocessa_silver_atualizada(camadas):
    camadas.acrescentar_bronze([registro()])
    camadas.executar()

    assert camadas.garantir() is False


def test_garantir_reprocessa_depois_de_dado_novo(camadas):
    camadas.acrescentar_bronze([registro(nome="a.jpg")])
    camadas.executar()
    camadas.acrescentar_bronze([registro(nome="b.jpg")])

    assert camadas.garantir() is True
    assert len(camadas.ler_camada(camadas.SILVER)) == 2


def test_limpar_apaga_as_tres_camadas(camadas):
    camadas.acrescentar_bronze([registro()])
    camadas.executar()
    camadas.limpar()

    assert not camadas.BRONZE.exists()
    assert not camadas.SILVER.exists()
    assert not camadas.GOLD.exists()


def test_acentos_sobrevivem_a_ida_e_volta(camadas):
    camadas.acrescentar_bronze([registro(localidade="Talhão São José", categoria="Saudável")])
    camadas.executar()
    silver = camadas.ler_camada(camadas.SILVER)

    assert silver.loc[0, "localidade"] == "Talhão São José"
    assert silver.loc[0, "categoria"] == "Saudável"
