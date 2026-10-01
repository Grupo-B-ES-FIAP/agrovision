"""Testes da carga do modelo e da predicao."""

import joblib
import numpy as np
import pytest
from conftest import imagem_solida
from sklearn.ensemble import RandomForestClassifier

from agrovision import modelo as mod
from agrovision.vision import N_CARACTERISTICAS, de_imagem


def treinar_modelo_falso(n_caracteristicas: int):
    """Treina um modelo minimo, usado so para exercitar a carga e a predicao."""
    gerador = np.random.default_rng(0)
    X = gerador.random((20, n_caracteristicas))
    y = np.array([0, 1] * 10)
    floresta = RandomForestClassifier(n_estimators=5, random_state=0)
    floresta.fit(X, y)
    return floresta


def test_modelo_ausente_da_mensagem_com_o_comando(tmp_path):
    mod.carregar.cache_clear()

    with pytest.raises(FileNotFoundError, match="treinar_modelo.py"):
        mod.carregar(tmp_path / "nao_existe.pkl")


def test_vetor_de_tamanho_errado_levanta_erro(tmp_path):
    """Troca uma falha silenciosa de predicao por um erro claro."""
    caminho = tmp_path / "modelo_errado.pkl"
    joblib.dump(treinar_modelo_falso(N_CARACTERISTICAS + 10), caminho)
    mod.carregar.cache_clear()

    with pytest.raises(ValueError, match="caracteristicas"):
        mod.carregar(caminho)


def test_prever_devolve_categoria_valida_e_confianca_em_porcentagem(tmp_path):
    caminho = tmp_path / "modelo.pkl"
    joblib.dump(treinar_modelo_falso(N_CARACTERISTICAS), caminho)
    mod.carregar.cache_clear()

    carregado = mod.carregar(caminho)
    categoria, confianca = mod.prever(carregado, de_imagem(imagem_solida((40, 160, 40))))

    assert categoria in mod.CATEGORIAS
    assert 0.0 <= confianca <= 100.0


def test_modelo_do_repositorio_carrega_e_classifica():
    """O modelo versionado precisa casar com a extracao de caracteristicas."""
    mod.carregar.cache_clear()
    floresta = mod.carregar()

    categoria, confianca = mod.prever(floresta, de_imagem(imagem_solida((40, 160, 40))))

    assert categoria in mod.CATEGORIAS
    assert confianca >= 50.0
