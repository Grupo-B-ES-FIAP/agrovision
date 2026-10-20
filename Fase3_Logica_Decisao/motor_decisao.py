"""Motor de regras da Fase 3. Usa exclusivamente a camada Silver (CSV tratado)."""
import csv
import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
ENTRADA = BASE / "dados" / "analises_tratadas.csv"
SAIDA = BASE / "dados" / "alertas.json"


def avaliar(registros):
    """Retorna decisões por talhão e por data; ignora registros sem data/categoria válida."""
    grupos = defaultdict(list)
    for r in registros:
        try:
            dia = date.fromisoformat(str(r.get("data", "")).strip()[:10])
        except ValueError:
            continue
        categoria = str(r.get("categoria", "")).strip().casefold()
        if categoria not in ("doente", "saudável", "saudavel"):
            continue
        talhao = str(r.get("localidade", "")).strip() or "Não informado"
        grupos[(talhao, dia)].append(categoria == "doente")

    diarios = defaultdict(dict)
    for (talhao, dia), flags in grupos.items():
        qtd = len(flags)
        doentes = sum(flags)
        percentual = round(100 * doentes / qtd, 2)
        diarios[talhao][dia] = {"data": dia.isoformat(), "total": qtd,
                                 "doentes": doentes, "percentual_doentes": percentual}

    alertas = []
    for talhao, por_dia in sorted(diarios.items()):
        for dia in sorted(por_dia):
            item = por_dia[dia]
            pct = item["percentual_doentes"]
            # Persistência: pelo menos uma folha doente em cada um dos 3 dias corridos.
            persistente = all((dia - timedelta(days=i)) in por_dia and
                              por_dia[dia - timedelta(days=i)]["doentes"] > 0
                              for i in range(3))
            critico = pct > 30
            atencao = 10 < pct <= 30
            normal = not (critico or atencao)
            prioridade = critico and persistente  # AND
            acao_controle = critico or persistente  # OR
            if prioridade:
                nivel, regra = "PRIORIDADE MÁXIMA", "R5"
                mensagem = "Solicitar avaliação agronômica prioritária e plano de controle."
            elif critico:
                nivel, regra = "CRÍTICO", "R3"
                mensagem = "Investigar possível infestação e intensificar inspeções."
            elif persistente:
                nivel, regra = "PERSISTÊNCIA", "R4"
                mensagem = "Solicitar avaliação agronômica por persistência de folhas doentes."
            elif atencao:
                nivel, regra = "ATENÇÃO", "R2"
                mensagem = "Aumentar monitoramento e repetir amostragem."
            else:
                nivel, regra = "NORMAL", "R1"
                mensagem = "Manter monitoramento de rotina."
            alertas.append({**item, "talhao": talhao, "nivel": nivel,
                            "regra": regra, "persistencia_3_dias": persistente,
                            "controle_recomendado": acao_controle,
                            "situacao_normal": normal, "recomendacao": mensagem})
    return alertas


def executar(entrada=ENTRADA, saida=SAIDA):
    if not Path(entrada).exists():
        raise FileNotFoundError(f"CSV tratado não encontrado: {entrada}")
    with Path(entrada).open(encoding="utf-8-sig", newline="") as f:
        registros = list(csv.DictReader(f, delimiter=";"))
    alertas = avaliar(registros)
    documento = {"gerado_em": datetime.now().isoformat(timespec="seconds"),
                 "fonte": str(Path(entrada).name), "criterios_experimentais": True,
                 "alertas": alertas}
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_text(json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8")
    return documento


if __name__ == "__main__":
    resultado = executar()
    print(f"{len(resultado['alertas'])} decisões registradas em {SAIDA}")
