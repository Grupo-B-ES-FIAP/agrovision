"""Produtor da Fase 3: simula a chegada de dados novos do campo.

Entrega a base de demonstracao um dia por vez, como lote_AAAA-MM-DD.csv, na
pasta que a ingestao vigia. Cada entrega continua do dia seguinte ao ultimo lote.
"""

import shutil
import time
from pathlib import Path

from agrovision.esquema import DATA
from agrovision.exportacao import escrever_csv, ler_csv

RAIZ = Path(__file__).resolve().parents[2]
BASE = RAIZ / "data" / "exemplos" / "analises_demo.csv"

PREFIXO = "lote_"
SUFIXO_REENVIO = "_reenvio"


def entregues(destino: Path) -> list[str]:
    """Datas dos lotes ja entregues, em ordem. Ignora os reenvios."""
    return sorted(
        arquivo.stem.removeprefix(PREFIXO)
        for arquivo in Path(destino).glob(f"{PREFIXO}*.csv")
        if not arquivo.stem.endswith(SUFIXO_REENVIO)
    )


def gravar(caminho: Path, registros: list[dict]) -> None:
    """Grava em .tmp e renomeia, para a ingestao nunca ler o arquivo pela metade."""
    temporario = caminho.with_suffix(".tmp")
    escrever_csv(temporario, registros)
    temporario.replace(caminho)


def entregar(destino: Path, lotes: int = 1, intervalo: float = 0, aviso=print) -> list[Path]:
    """Entrega os proximos `lotes` dias da base. Levanta ValueError se acabaram."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)

    por_dia: dict[str, list[dict]] = {}
    for registro in ler_csv(BASE):
        por_dia.setdefault(registro[DATA], []).append(registro)

    ja_entregues = set(entregues(destino))
    restantes = [dia for dia in sorted(por_dia) if dia not in ja_entregues]
    if not restantes:
        raise ValueError("Todos os dias da base ja foram entregues.")

    arquivos = []
    for i, dia in enumerate(restantes[:lotes]):
        if i and intervalo:
            time.sleep(intervalo)

        arquivo = destino / f"{PREFIXO}{dia}.csv"
        gravar(arquivo, por_dia[dia])
        aviso(f"{arquivo.name} gravado: {len(por_dia[dia])} registro(s) em {destino}")
        arquivos.append(arquivo)

    return arquivos


def reenviar(destino: Path) -> Path:
    """Copia o ultimo lote entregue. Levanta ValueError se nao ha lote."""
    destino = Path(destino)
    ultimos = entregues(destino)
    if not ultimos:
        raise ValueError("Nenhum lote entregue para reenviar.")

    origem = destino / f"{PREFIXO}{ultimos[-1]}.csv"
    copia = destino / f"{PREFIXO}{ultimos[-1]}{SUFIXO_REENVIO}.csv"
    shutil.copyfile(origem, copia)
    return copia


def reiniciar(destino: Path) -> None:
    """Deixa a pasta vazia: apaga lotes, reenvios e qualquer arquivo de dados."""
    for arquivo in Path(destino).glob("*"):
        if arquivo.is_file() and arquivo.suffix.lower() in {".csv", ".json", ".tmp"}:
            arquivo.unlink()
