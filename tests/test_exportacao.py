"""Testes do formato de exportacao em CSV e JSON (item 1.2 da Fase 1)."""

import json

from conftest import registro

from agrovision.esquema import CAMPOS
from agrovision.exportacao import escrever_csv, gerar_csv, gerar_json, ler_csv


def test_csv_comeca_com_bom():
    """O BOM faz o Excel em portugues abrir o arquivo com os acentos corretos."""
    assert gerar_csv([registro()]).startswith("﻿")


def test_csv_tem_o_cabecalho_do_contrato():
    linhas = gerar_csv([registro()]).lstrip("﻿").splitlines()

    assert linhas[0] == ";".join(CAMPOS)


def test_csv_mantem_a_ordem_das_colunas_com_dicionario_desordenado():
    bagunçado = {campo: campo for campo in reversed(CAMPOS)}
    linhas = gerar_csv([bagunçado]).lstrip("﻿").splitlines()

    assert linhas[1] == ";".join(CAMPOS)


def test_csv_preenche_campo_ausente_com_vazio():
    linhas = gerar_csv([{"nome_imagem": "folha.jpg"}]).lstrip("﻿").splitlines()

    assert linhas[1] == "folha.jpg;;;;;"


def test_json_tem_total_e_resultados():
    pacote = json.loads(gerar_json([registro(), registro(nome="outra.jpg")]))

    assert pacote["total_imagens"] == 2
    assert len(pacote["resultados"]) == 2
    assert list(pacote["resultados"][0]) == CAMPOS
    assert "gerado_em" in pacote


def test_json_de_lista_vazia_e_valido():
    pacote = json.loads(gerar_json([]))

    assert pacote["total_imagens"] == 0
    assert pacote["resultados"] == []


def test_json_nao_escapa_acentos():
    assert "Saudável" in gerar_json([registro(categoria="Saudável")])


def test_gravar_e_ler_devolve_os_mesmos_valores(tmp_path):
    caminho = tmp_path / "analises.csv"
    escrever_csv(caminho, [registro(localidade="Talhão São José")])
    lido = ler_csv(caminho)

    assert len(lido) == 1
    assert lido[0]["localidade"] == "Talhão São José"
    assert lido[0]["nome_imagem"] == "folha.jpg"


def test_gravar_coloca_um_unico_bom(tmp_path):
    """Dois BOM quebrariam o nome da primeira coluna na leitura."""
    caminho = tmp_path / "analises.csv"
    escrever_csv(caminho, [registro()])

    assert caminho.read_bytes().count(b"\xef\xbb\xbf") == 1


def test_ler_arquivo_inexistente_devolve_lista_vazia(tmp_path):
    assert ler_csv(tmp_path / "nao_existe.csv") == []
