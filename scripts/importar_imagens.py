"""Classifica em lote uma pasta de imagens e grava na camada Bronze.

Uso:
    python scripts/importar_imagens.py <pasta> <localidade> [data AAAA-MM-DD]

Exemplo:
    python scripts/importar_imagens.py data/dataset/doente "Talhao A" 2026-09-10

Depois da importacao, rode o pipeline para atualizar o painel:
    python -m agrovision.pipeline
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agrovision.esquema import EXTENSOES_IMAGEM  # noqa: E402
from agrovision.modelo import carregar, prever  # noqa: E402
from agrovision.pipeline import acrescentar_bronze  # noqa: E402
from agrovision.vision import de_arquivo  # noqa: E402


def importar(pasta: str, localidade: str, data_coleta: str) -> int:
    """Classifica cada imagem da pasta e devolve quantas foram gravadas."""
    modelo = carregar()
    registros = []

    for caminho in sorted(Path(pasta).iterdir()):
        if caminho.suffix.lower() not in EXTENSOES_IMAGEM:
            continue

        caracteristicas = de_arquivo(caminho)

        if caracteristicas is None:
            print(f"Aviso: nao foi possivel ler {caminho.name}")
            continue

        categoria, confianca = prever(modelo, caracteristicas)
        registros.append(
            {
                "nome_imagem": caminho.name,
                "categoria": categoria,
                "acuracia": confianca,
                "data": data_coleta,
                "localidade": localidade,
                "origem": "Modelo (lote)",
            }
        )
        print(f"{caminho.name}: {categoria} ({confianca:.2f}%)")

    if not registros:
        print("Nenhuma imagem valida encontrada na pasta informada.")
        return 0

    acrescentar_bronze(registros)
    print(f"\n{len(registros)} imagem(ns) gravada(s) na camada Bronze.")
    return len(registros)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    data = sys.argv[3] if len(sys.argv) > 3 else date.today().isoformat()
    importar(sys.argv[1], sys.argv[2], data)
