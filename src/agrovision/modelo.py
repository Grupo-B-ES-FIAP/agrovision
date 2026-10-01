"""Carga do classificador treinado e predicao de uma folha."""

from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np

from agrovision.vision import N_CARACTERISTICAS

RAIZ = Path(__file__).resolve().parents[2]
CAMINHO_MODELO = RAIZ / "models" / "modelo_folhas.pkl"

SAUDAVEL = "Saudável"
DOENTE = "Doente"
CATEGORIAS = (SAUDAVEL, DOENTE)


@lru_cache(maxsize=1)
def carregar(caminho: Path | None = None):
    """Carrega o modelo e confere o tamanho do vetor que ele espera.

    Se o treino mudar o vetor de caracteristicas e o modelo nao for treinado de
    novo, a predicao devolveria lixo em silencio. A conferencia abaixo troca
    essa falha silenciosa por um erro claro.
    """
    caminho = caminho or CAMINHO_MODELO

    if not caminho.exists():
        raise FileNotFoundError(
            f"Modelo nao encontrado em {caminho}. "
            "Rode: python scripts/treinar_modelo.py"
        )

    modelo = joblib.load(caminho)
    esperado = getattr(modelo, "n_features_in_", N_CARACTERISTICAS)

    if esperado != N_CARACTERISTICAS:
        raise ValueError(
            f"O modelo espera {esperado} caracteristicas e a extracao produz "
            f"{N_CARACTERISTICAS}. Treine o modelo de novo com "
            "python scripts/treinar_modelo.py"
        )

    return modelo


def prever(modelo, caracteristicas: np.ndarray) -> tuple[str, float]:
    """Classifica um vetor de caracteristicas.

    Devolve a categoria e a confianca em porcentagem. A confianca e a
    probabilidade que o modelo atribui a classe escolhida, nao a acuracia do
    modelo como um todo.
    """
    entrada = caracteristicas.reshape(1, -1)
    indice = int(modelo.predict(entrada)[0])
    confianca = round(float(max(modelo.predict_proba(entrada)[0]) * 100), 2)

    return CATEGORIAS[indice], confianca
