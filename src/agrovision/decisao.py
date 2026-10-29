"""Motor de regras da Fase 3: transforma as analises em decisoes por talhao e dia.

As regras estao descritas em Fase3_Logica_Decisao/Regras_e_Fluxograma.pdf:

- R1 Normal: ate 10% de folhas doentes, sem persistencia.
- R2 Atencao: mais de 10% e ate 30% de folhas doentes, sem persistencia.
- R3 Critico: mais de 30% de folhas doentes, sem persistencia.
- R4 Persistencia: folha doente em cada um de 3 dias seguidos no mesmo talhao.
- R5 Prioridade maxima: R3 AND R4.

A prioridade de avaliacao e R5, R3, R4, R2 e R1. Os limiares sao didaticos,
nao parametros agronomicos validados.
"""

from collections import defaultdict
from datetime import date, timedelta

from agrovision.esquema import CATEGORIA, DATA, DOENTE, LOCALIDADE, SAUDAVEL

LIMIAR_CRITICO = 30
LIMIAR_ATENCAO = 10
DIAS_PERSISTENCIA = 3

SEM_LOCALIDADE = "Não informado"

# Regra -> (nivel, recomendacao). A ordem segue a prioridade de avaliacao.
REGRAS = {
    "R5": (
        "PRIORIDADE MÁXIMA",
        "Solicitar avaliação agronômica prioritária e plano de controle.",
    ),
    "R3": ("CRÍTICO", "Investigar possível infestação e intensificar inspeções."),
    "R4": (
        "PERSISTÊNCIA",
        "Solicitar avaliação agronômica por persistência de folhas doentes.",
    ),
    "R2": ("ATENÇÃO", "Aumentar monitoramento e repetir amostragem."),
    "R1": ("NORMAL", "Manter monitoramento de rotina."),
}

# Regras que pedem alguma intervencao no talhao.
REGRAS_DE_INTERVENCAO = {"R5", "R3", "R4"}


def _agrupar(registros) -> dict:
    """Conta folhas e folhas doentes por talhao e dia.

    Ignora registros sem data valida ou com categoria fora do contrato.
    """
    contagem = defaultdict(lambda: [0, 0])
    validas = {SAUDAVEL.casefold(), DOENTE.casefold()}

    for registro in registros:
        try:
            dia = date.fromisoformat(str(registro.get(DATA, "")).strip()[:10])
        except ValueError:
            continue

        categoria = str(registro.get(CATEGORIA, "")).strip().casefold()
        if categoria not in validas:
            continue

        talhao = str(registro.get(LOCALIDADE, "")).strip() or SEM_LOCALIDADE
        contagem[(talhao, dia)][0] += 1
        contagem[(talhao, dia)][1] += categoria == DOENTE.casefold()

    diarios = defaultdict(dict)
    for (talhao, dia), (total, doentes) in contagem.items():
        diarios[talhao][dia] = {
            "data": dia.isoformat(),
            "total": total,
            "doentes": doentes,
            "percentual_doentes": round(100 * doentes / total, 2),
        }

    return diarios


def avaliar(registros) -> list[dict]:
    """Aplica as regras R1 a R5 e devolve uma decisao por talhao e dia."""
    alertas = []

    for talhao, por_dia in sorted(_agrupar(registros).items()):
        for dia in sorted(por_dia):
            item = por_dia[dia]
            pct = item["percentual_doentes"]

            # Persistencia: pelo menos uma folha doente em cada dia da janela.
            janela = [dia - timedelta(days=i) for i in range(DIAS_PERSISTENCIA)]
            persistente = all(d in por_dia and por_dia[d]["doentes"] > 0 for d in janela)

            critico = pct > LIMIAR_CRITICO
            atencao = LIMIAR_ATENCAO < pct <= LIMIAR_CRITICO
            normal = not (critico or atencao)  # NOT

            if critico and persistente:  # AND
                regra = "R5"
            elif critico:
                regra = "R3"
            elif persistente:
                regra = "R4"
            elif atencao:
                regra = "R2"
            else:
                regra = "R1"

            nivel, recomendacao = REGRAS[regra]
            alertas.append(
                {
                    **item,
                    "talhao": talhao,
                    "nivel": nivel,
                    "regra": regra,
                    "persistencia_3_dias": persistente,
                    "controle_recomendado": critico or persistente,  # OR
                    "situacao_normal": normal,
                    "recomendacao": recomendacao,
                }
            )

    return alertas


def situacao_atual(alertas: list[dict]) -> list[dict]:
    """Ultima decisao de cada talhao, que e a situacao a tratar agora."""
    ultimos = {}
    for alerta in alertas:
        atual = ultimos.get(alerta["talhao"])
        if atual is None or alerta["data"] > atual["data"]:
            ultimos[alerta["talhao"]] = alerta

    return [ultimos[talhao] for talhao in sorted(ultimos)]
