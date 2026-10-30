"""Simula a chegada de dados novos do campo para a ingestao da Fase 3.

Entrega a base de demonstracao um dia por vez, como lote_AAAA-MM-DD.csv, em
data/entrada/demonstracao. Cada execucao continua do dia seguinte.

    python scripts/gerar_lotes.py                            # proximo dia
    python scripts/gerar_lotes.py --lotes 5 --intervalo 10   # 5 dias, um a cada 10 s
    python scripts/gerar_lotes.py --reenviar                 # copia o ultimo lote
    python scripts/gerar_lotes.py --reiniciar                # esvazia a pasta
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agrovision import produtor  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ / "data" / "entrada" / "demonstracao"


def main(argumentos=None) -> None:
    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leitor.add_argument("--lotes", type=int, default=1, help="quantos dias entregar")
    leitor.add_argument("--intervalo", type=float, default=0, help="segundos entre os lotes")
    leitor.add_argument("--destino", type=Path, default=DESTINO, help="pasta de entrada")
    leitor.add_argument("--reenviar", action="store_true", help="copia o ultimo lote de novo")
    leitor.add_argument("--reiniciar", action="store_true", help="esvazia a pasta e encerra")
    opcoes = leitor.parse_args(argumentos)

    opcoes.destino.mkdir(parents=True, exist_ok=True)

    try:
        if opcoes.reiniciar:
            produtor.reiniciar(opcoes.destino)
            print(f"Pasta esvaziada: {opcoes.destino}")
            return

        if opcoes.reenviar:
            copia = produtor.reenviar(opcoes.destino)
            print(f"{copia.name} gravado: copia do ultimo lote")
            return

        produtor.entregar(opcoes.destino, opcoes.lotes, opcoes.intervalo)
    except ValueError as erro:
        sys.exit(f"{erro} Use --reiniciar para recomecar." if "entregues" in str(erro) else erro)


if __name__ == "__main__":
    main()
