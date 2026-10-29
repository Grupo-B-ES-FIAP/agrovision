"""Testes da automacao: arquivos gerados e disparo pelo pipeline."""

import json

from conftest import registro

from agrovision import automacao


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


def test_grava_alertas_e_relatorio(tmp_path):
    registros = lote("Talhão A", "2026-09-10", 5) + lote("Talhão B", "2026-09-10", 0)

    resultado = automacao.executar(registros, tmp_path)

    alertas = json.loads(resultado["arquivo_alertas"].read_text(encoding="utf-8"))
    assert [a["regra"] for a in alertas["alertas"]] == ["R3", "R1"]

    relatorio = resultado["arquivo_relatorio"].read_text(encoding="utf-8")
    assert resultado["arquivo_relatorio"].parent == tmp_path / "relatorios"
    assert "Talhão A: CRÍTICO (R3)" in relatorio
    assert "Talhão B: " not in relatorio


def test_relatorio_sem_dados(tmp_path):
    resultado = automacao.executar([], tmp_path)

    assert resultado["alertas"] == []
    assert "Nada a recomendar" in resultado["relatorio"]


def test_pipeline_dispara_a_automacao(camadas):
    for dia in ("2026-09-10", "2026-09-11", "2026-09-12"):
        camadas.acrescentar_bronze(lote("Talhão A", dia, 4))

    camadas.executar()

    alertas = json.loads(camadas.ALERTAS.read_text(encoding="utf-8"))["alertas"]
    assert alertas[-1]["regra"] == "R5"
    assert list((camadas.SAIDA / "relatorios").glob("intervencao_*.md"))


def test_limpar_apaga_os_alertas(camadas):
    camadas.acrescentar_bronze(lote("Talhão A", "2026-09-10", 1))
    camadas.executar()

    camadas.limpar()

    assert not camadas.ALERTAS.exists()


def test_linha_de_comando_com_demonstracao(camadas, capsys):
    automacao.main(["--demo"])

    saida = capsys.readouterr().out
    assert "Talhão B" in saida
    # A demonstracao nao pode sobrescrever os alertas dos dados reais.
    assert (camadas.SAIDA / "demonstracao" / "alertas.json").exists()
    assert not camadas.ALERTAS.exists()
