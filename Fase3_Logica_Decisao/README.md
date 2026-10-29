# AgroVision — Fase 3 | Lógica de decisão

Contribuição individual para o projeto em grupo **AgroSmart / AgroVision**. Implementa o requisito **1 — Definição da lógica de decisão**, com regras condicionais, operadores booleanos e fluxograma.

## Arquivos

| Arquivo | Finalidade |
| --- | --- |
| `src/agrovision/decisao.py` | Motor de regras R1–R5 (antes `motor_decisao.py`) |
| `tests/test_decisao.py` | Testes pytest das regras (antes `teste_regras.py`) |
| `Regras_e_Fluxograma.pdf` | Documento do requisito 1 |
| `Evidencia_Testes.png` | Captura do terminal com os cinco testes aprovados |
| `INTEGRACAO.md` | Onde cada parte foi integrada no repositório principal |

## Regras

- **R1 Normal:** até 10% de folhas doentes e sem persistência.
- **R2 Atenção:** mais de 10% e até 30% de folhas doentes, sem persistência.
- **R3 Crítico:** mais de 30% de folhas doentes, sem persistência.
- **R4 Persistência:** pelo menos uma folha classificada como doente em cada um de três dias corridos no mesmo talhão, desde que R5 não se aplique.
- **R5 Prioridade máxima:** percentual de doentes acima de 30% **AND** persistência de três dias.

O motor usa **AND**, **OR** e **NOT**. A prioridade das regras é R5, R3, R4, R2 e R1. Os alertas são *recomendações*, não acionamentos físicos.

## Executar testes

Na raiz do repositório, com o projeto instalado (`pip install -e ".[dev]"`):

```bash
pytest tests/test_decisao.py
```

## Executar com dados reais

O motor lê a camada Silver do pipeline, `data/saida/analises_tratadas.csv`. A automação do passo 2 roda as regras a cada análise nova e grava `data/saida/alertas.json`. Para rodar à mão:

```bash
python -m agrovision.automacao
```

A descrição completa da automação está em [docs/fase3-automacao.md](../docs/fase3-automacao.md).

## Limitações

Os limiares são didáticos, não parâmetros agronômicos validados. O classificador diferencia apenas **Saudável/Doente**, sem identificar a espécie de praga. A persistência exige observações em três datas corridas consecutivas no mesmo talhão; a ausência de dados em um dia interrompe a sequência. A amostra da Fase 2 é pequena.

## Status

As regras R1–R5 foram aprovadas em testes simulados executados localmente; veja `Evidencia_Testes.png`. Depois da integração, os mesmos cenários rodam no CI em `tests/test_decisao.py`, e a aba Inteligência no campo do aplicativo exibe as decisões.
