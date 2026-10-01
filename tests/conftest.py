"""Acessorios compartilhados pelos testes."""

import numpy as np
import pytest

from agrovision import pipeline


@pytest.fixture
def camadas(tmp_path, monkeypatch):
    """Aponta as tres camadas do pipeline para uma pasta temporaria.

    Sem isso, os testes escreveriam em data/saida e apagariam dados reais.
    """
    saida = tmp_path / "saida"
    saida.mkdir()

    monkeypatch.setattr(pipeline, "SAIDA", saida)
    monkeypatch.setattr(pipeline, "BRONZE", saida / "analises.csv")
    monkeypatch.setattr(pipeline, "SILVER", saida / "analises_tratadas.csv")
    monkeypatch.setattr(pipeline, "GOLD", saida / "indicadores.json")

    return pipeline


def registro(nome="folha.jpg", categoria="Saudável", acuracia=95.0,
             data="2026-09-10", localidade="Talhão A", origem="Modelo"):
    """Monta um registro de analise valido, com campos sobrescreviveis."""
    return {
        "nome_imagem": nome,
        "categoria": categoria,
        "acuracia": acuracia,
        "data": data,
        "localidade": localidade,
        "origem": origem,
    }


def imagem_solida(bgr):
    """Cria uma imagem 64 por 64 de uma cor so, no formato BGR do OpenCV."""
    imagem = np.zeros((64, 64, 3), dtype=np.uint8)
    imagem[:, :] = bgr
    return imagem
