"""Exportacao dos resultados em CSV e JSON (item 1.2 da Fase 1)."""

import csv
import io
import json
from datetime import datetime

from agrovision.esquema import CAMPOS, CODIFICACAO, SEPARADOR

__all__ = ["CAMPOS", "gerar_csv", "gerar_json"]

BOM = "﻿"


def gerar_csv(resultados: list[dict]) -> str:
    """Monta o CSV das analises, com as colunas sempre na mesma ordem."""
    buffer = io.StringIO()
    escritor = csv.DictWriter(buffer, fieldnames=CAMPOS, delimiter=SEPARADOR)
    escritor.writeheader()

    for linha in resultados:
        escritor.writerow({campo: linha.get(campo, "") for campo in CAMPOS})

    # O BOM faz o Excel em portugues abrir o arquivo com os acentos corretos.
    return BOM + buffer.getvalue()


def gerar_json(resultados: list[dict]) -> str:
    """Monta o JSON das analises, com data de geracao e total."""
    pacote = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "total_imagens": len(resultados),
        "resultados": [
            {campo: linha.get(campo, "") for campo in CAMPOS} for linha in resultados
        ],
    }

    return json.dumps(pacote, ensure_ascii=False, indent=2)


def escrever_csv(caminho, resultados: list[dict]) -> None:
    """Grava as analises em disco no mesmo formato da exportacao.

    A gravacao usa utf-8 puro porque gerar_csv ja coloca o BOM no inicio.
    Gravar com utf-8-sig acrescentaria um segundo BOM.
    """
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(gerar_csv(resultados), encoding="utf-8", newline="")


def ler_csv(caminho) -> list[dict]:
    """Le um CSV de analises. Devolve lista vazia quando o arquivo nao existe."""
    if not caminho.exists():
        return []

    with caminho.open(encoding=CODIFICACAO, newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=SEPARADOR))
