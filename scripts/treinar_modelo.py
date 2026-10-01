"""Treina o classificador de folhas e grava o modelo e as metricas.

Uso:
    python scripts/treinar_modelo.py

Saida:
    models/modelo_folhas.pkl   modelo treinado
    models/metrics.json        acuracia e relatorio por classe, auditaveis
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agrovision.modelo import CATEGORIAS  # noqa: E402
from agrovision.vision import N_CARACTERISTICAS, de_arquivo  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
PASTAS = {
    0: RAIZ / "data" / "dataset" / "saudavel",
    1: RAIZ / "data" / "dataset" / "doente",
}
MODELO = RAIZ / "models" / "modelo_folhas.pkl"
METRICAS = RAIZ / "models" / "metrics.json"

SEMENTE = 42
PROPORCAO_TESTE = 0.20
ARVORES = 200


def carregar_pasta(pasta: Path, classe: int) -> tuple[list, list]:
    """Le todas as imagens de uma pasta e devolve os vetores e as classes."""
    vetores, classes = [], []

    for caminho in sorted(pasta.iterdir()):
        caracteristicas = de_arquivo(caminho)

        if caracteristicas is None:
            print(f"Aviso: nao foi possivel ler {caminho.name}")
            continue

        vetores.append(caracteristicas)
        classes.append(classe)

    return vetores, classes


def main() -> None:
    print("Carregando imagens...")
    vetores, classes = [], []

    for classe, pasta in PASTAS.items():
        if not pasta.exists():
            raise FileNotFoundError(f"Pasta de imagens nao encontrada: {pasta}")

        novos_vetores, novas_classes = carregar_pasta(pasta, classe)
        vetores += novos_vetores
        classes += novas_classes
        print(f"  {CATEGORIAS[classe]}: {len(novos_vetores)} imagens")

    X = np.array(vetores)
    y = np.array(classes)
    print(f"Total: {len(X)} imagens, {X.shape[1]} caracteristicas por imagem")

    if X.shape[1] != N_CARACTERISTICAS:
        raise ValueError(
            f"A extracao produziu {X.shape[1]} caracteristicas e o modulo "
            f"declara {N_CARACTERISTICAS}."
        )

    X_treino, X_teste, y_treino, y_teste = train_test_split(
        X, y, test_size=PROPORCAO_TESTE, random_state=SEMENTE, stratify=y
    )

    print("\nTreinando modelo...")
    modelo = RandomForestClassifier(n_estimators=ARVORES, random_state=SEMENTE)
    modelo.fit(X_treino, y_treino)

    previsoes = modelo.predict(X_teste)
    acuracia = accuracy_score(y_teste, previsoes)
    relatorio = classification_report(
        y_teste, previsoes, target_names=list(CATEGORIAS), output_dict=True
    )

    print("\n-----------------------------")
    print("RESULTADO DO TREINAMENTO")
    print("-----------------------------")
    print(f"Acuracia: {acuracia * 100:.2f}%")
    print("\nRelatorio:")
    print(classification_report(y_teste, previsoes, target_names=list(CATEGORIAS)))

    MODELO.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, MODELO)

    METRICAS.write_text(
        json.dumps(
            {
                "treinado_em": datetime.now().isoformat(timespec="seconds"),
                "modelo": "RandomForestClassifier",
                "arvores": ARVORES,
                "semente": SEMENTE,
                "proporcao_teste": PROPORCAO_TESTE,
                "total_imagens": int(len(X)),
                "imagens_treino": int(len(X_treino)),
                "imagens_teste": int(len(X_teste)),
                "n_caracteristicas": int(X.shape[1]),
                "acuracia": round(float(acuracia), 4),
                "relatorio_por_classe": relatorio,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nModelo salvo em: {MODELO.relative_to(RAIZ)}")
    print(f"Metricas salvas em: {METRICAS.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
