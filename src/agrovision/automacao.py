"""Automacao da Fase 3: resposta do sistema as regras de decisao.

Cada execucao le as analises, aplica as regras R1 a R5 de agrovision.decisao e
grava dois arquivos na pasta de saida:

- alertas.json: uma decisao por talhao e dia, para outros sistemas consumirem.
- relatorios/intervencao_<data>_<hora>.md: relatorio de intervencao para o
  produtor, com a situacao atual de cada talhao e a acao recomendada.

O pipeline chama executar() ao fim de cada carga, entao toda analise nova gera
alertas e relatorio sem acao manual. Para rodar sozinho:
    python -m agrovision.automacao          (camada Silver)
    python -m agrovision.automacao --demo   (base de demonstracao)
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from agrovision.decisao import (
    DIAS_PERSISTENCIA,
    LIMIAR_ATENCAO,
    LIMIAR_CRITICO,
    REGRAS,
    REGRAS_DE_INTERVENCAO,
    avaliar,
    situacao_atual,
)

RAIZ = Path(__file__).resolve().parents[2]
DEMO = RAIZ / "data" / "exemplos" / "analises_demo.csv"

ALERTAS = "alertas.json"
RELATORIOS = "relatorios"


def _linha(*celulas) -> str:
    return "| " + " | ".join(str(celula) for celula in celulas) + " |"


def gerar_relatorio(alertas: list[dict], gerado_em: str, fonte: str) -> str:
    """Monta o relatorio de intervencao em Markdown."""
    linhas = [
        "# Relatório de intervenção | AgroVision",
        "",
        f"- Gerado em: {gerado_em}",
        f"- Fonte dos dados: {fonte}",
        "",
        f"Critérios experimentais: crítico acima de {LIMIAR_CRITICO}% de folhas doentes, "
        f"atenção acima de {LIMIAR_ATENCAO}%, persistência em {DIAS_PERSISTENCIA} dias "
        "seguidos. As recomendações não acionam nenhum equipamento.",
        "",
    ]

    if not alertas:
        linhas.append("Nenhuma análise válida encontrada. Nada a recomendar.")
        return "\n".join(linhas) + "\n"

    atual = situacao_atual(alertas)
    linhas += [
        "## Situação atual por talhão",
        "",
        _linha("Talhão", "Último dia", "Folhas", "Doentes", "% doentes", "Regra", "Nível",
               "Ação recomendada"),
        _linha(*["---"] * 8),
    ]
    for a in atual:
        linhas.append(_linha(a["talhao"], a["data"], a["total"], a["doentes"],
                             f"{a['percentual_doentes']:.1f}%", a["regra"], a["nivel"],
                             a["recomendacao"]))

    linhas += ["", "## Talhões que pedem intervenção", ""]
    intervir = [a for a in atual if a["regra"] in REGRAS_DE_INTERVENCAO]
    if intervir:
        for a in intervir:
            linhas.append(f"- {a['talhao']}: {a['nivel']} ({a['regra']}) em {a['data']}. "
                          f"{a['recomendacao']}")
    else:
        linhas.append("Nenhum talhão pede intervenção agora. Manter monitoramento de rotina.")

    historico = [a for a in alertas if a["regra"] in REGRAS_DE_INTERVENCAO]
    linhas += ["", "## Dias com intervenção recomendada", ""]
    if historico:
        linhas += [_linha("Data", "Talhão", "% doentes", "Regra", "Nível"), _linha(*["---"] * 5)]
        for a in sorted(historico, key=lambda a: (a["data"], a["talhao"])):
            linhas.append(_linha(a["data"], a["talhao"], f"{a['percentual_doentes']:.1f}%",
                                 a["regra"], a["nivel"]))
    else:
        linhas.append("Nenhum dia atingiu as regras R3, R4 ou R5.")

    linhas += ["", "## Dias por regra", "", _linha("Regra", "Nível", "Dias"),
               _linha("---", "---", "---")]
    for regra, (nivel, _) in REGRAS.items():
        linhas.append(_linha(regra, nivel, sum(a["regra"] == regra for a in alertas)))

    return "\n".join(linhas) + "\n"


def executar(registros: list[dict], destino: Path, fonte: str = "camada Silver") -> dict:
    """Aplica as regras e grava alertas.json e o relatorio de intervencao."""
    agora = datetime.now()
    gerado_em = agora.isoformat(timespec="seconds")
    alertas = avaliar(registros)

    destino = Path(destino)
    pasta_relatorios = destino / RELATORIOS
    pasta_relatorios.mkdir(parents=True, exist_ok=True)

    arquivo_alertas = destino / ALERTAS
    documento = {
        "gerado_em": gerado_em,
        "fonte": fonte,
        "criterios_experimentais": True,
        "alertas": alertas,
    }
    arquivo_alertas.write_text(
        json.dumps(documento, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    arquivo_relatorio = pasta_relatorios / f"intervencao_{agora:%Y-%m-%d_%H%M%S}.md"
    relatorio = gerar_relatorio(alertas, gerado_em, fonte)
    arquivo_relatorio.write_text(relatorio, encoding="utf-8")

    return {
        **documento,
        "situacao": situacao_atual(alertas),
        "relatorio": relatorio,
        "arquivo_alertas": arquivo_alertas,
        "arquivo_relatorio": arquivo_relatorio,
    }


def main(argumentos=None) -> dict:
    # Importado aqui porque o pipeline importa este modulo.
    from agrovision import pipeline
    from agrovision.exportacao import ler_csv

    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leitor.add_argument("--demo", action="store_true", help="usa a base de demonstracao")
    opcoes = leitor.parse_args(argumentos)

    origem = DEMO if opcoes.demo else pipeline.SILVER
    fonte = "base de demonstração" if opcoes.demo else "camada Silver"
    registros = ler_csv(origem)
    print(f"[Automacao] {len(registros)} registro(s) lido(s) de {origem.name}")

    # A demonstracao grava em uma subpasta para nao sobrescrever os alertas reais.
    destino = pipeline.SAIDA / "demonstracao" if opcoes.demo else pipeline.SAIDA
    resultado = executar(registros, destino, fonte)

    for a in resultado["situacao"]:
        print(f"  {a['talhao']:<12} {a['data']}  {a['percentual_doentes']:>6.1f}%  "
              f"{a['regra']} {a['nivel']:<18} {a['recomendacao']}")

    print(f"[Automacao] {len(resultado['alertas'])} decisao(oes) em {resultado['arquivo_alertas']}")
    print(f"[Automacao] Relatorio de intervencao em {resultado['arquivo_relatorio']}")
    return resultado


if __name__ == "__main__":
    main()
