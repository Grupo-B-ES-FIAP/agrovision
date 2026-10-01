"""Gera a base de demonstracao do painel.

A base real do grupo tem poucos registros e cada talhao aparece com uma unica
classe, o que deixa os graficos sem informacao. Esta base simula 30 dias de
coleta em tres talhoes, com um foco de praga crescendo no Talhao B e caindo
depois da aplicacao de defensivo. Serve para apresentar o painel.

Os registros nao sao inferencias do modelo. A coluna origem marca Simulado.

Uso:
    python scripts/gerar_dados_demo.py

A semente e a data final sao fixas, logo o arquivo gerado e sempre o mesmo.
"""

import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agrovision.esquema import (  # noqa: E402
    ACURACIA,
    CATEGORIA,
    DATA,
    DOENTE,
    LOCALIDADE,
    NOME_IMAGEM,
    ORIGEM,
    ORIGEM_SIMULADO,
    SAUDAVEL,
)
from agrovision.exportacao import escrever_csv  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "data" / "exemplos" / "analises_demo.csv"

SEMENTE = 2026
DIA_FINAL = date(2026, 9, 30)
DIAS = 30
# Doze imagens por talhao por dia deixam a curva diaria legivel no painel.
# Com poucas imagens, o acaso domina o grafico e a historia desaparece.
IMAGENS_POR_DIA = 12

# Historia que a base conta, talhao por talhao:
# - Talhao A: lavoura sadia, poucos casos isolados.
# - Talhao B: foco de praga a partir do dia 10, pico no dia 18 e queda depois
#   da aplicacao de defensivo.
# - Talhao C: pressao media e estavel, exige monitoramento.
TALHAO_A = "Talhão A"
TALHAO_B = "Talhão B"
TALHAO_C = "Talhão C"

DIA_INICIO_FOCO = 8
DIA_PICO = 17
DIA_APLICACAO = 17
DIA_FIM_RECUPERACAO = 26


def risco_do_dia(talhao: str, dia: int) -> float:
    """Probabilidade de uma folha sair doente naquele talhao e naquele dia."""
    if talhao == TALHAO_A:
        return 0.08

    if talhao == TALHAO_C:
        return 0.18

    if dia < DIA_INICIO_FOCO:
        return 0.10

    if dia <= DIA_PICO:
        # Subida do foco: de 10% para 85% em nove dias.
        avanco = (dia - DIA_INICIO_FOCO) / (DIA_PICO - DIA_INICIO_FOCO)
        return 0.10 + 0.75 * avanco

    # Queda depois da aplicacao de defensivo, ate voltar ao nivel normal.
    recuperacao = min(1.0, (dia - DIA_APLICACAO) / (DIA_FIM_RECUPERACAO - DIA_APLICACAO))
    return 0.85 - 0.75 * recuperacao


def gerar() -> list[dict]:
    """Monta os registros de demonstracao."""
    sorteio = random.Random(SEMENTE)
    inicio = DIA_FINAL - timedelta(days=DIAS - 1)
    registros = []
    sequencia = 0

    for dia in range(DIAS):
        data_coleta = inicio + timedelta(days=dia)

        for talhao in (TALHAO_A, TALHAO_B, TALHAO_C):
            risco = risco_do_dia(talhao, dia)

            for _ in range(IMAGENS_POR_DIA):
                sequencia += 1
                doente = sorteio.random() < risco
                # Folha com mancha evidente da confianca mais alta que folha
                # no inicio da infeccao, por isso as faixas sao diferentes.
                confianca = (
                    sorteio.uniform(78.0, 99.0) if doente else sorteio.uniform(85.0, 100.0)
                )

                registros.append(
                    {
                        NOME_IMAGEM: f"demo_{sequencia:04d}.jpg",
                        CATEGORIA: DOENTE if doente else SAUDAVEL,
                        ACURACIA: round(confianca, 2),
                        DATA: data_coleta.isoformat(),
                        LOCALIDADE: talhao,
                        ORIGEM: ORIGEM_SIMULADO,
                    }
                )

    return registros


def main() -> None:
    registros = gerar()
    escrever_csv(SAIDA, registros)

    doentes = sum(1 for r in registros if r[CATEGORIA] == DOENTE)
    print(f"{len(registros)} registros gravados em {SAIDA.relative_to(RAIZ)}")
    print(f"Doentes: {doentes} ({doentes / len(registros):.1%})")
    print(f"Periodo: {registros[0][DATA]} a {registros[-1][DATA]}")


if __name__ == "__main__":
    main()
