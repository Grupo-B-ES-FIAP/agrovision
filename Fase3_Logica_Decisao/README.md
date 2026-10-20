# AgroVision — Fase 3 | Lógica de decisão

Contribuição individual para o projeto em grupo **AgroSmart / AgroVision**. Implementa o requisito **1 — Definição da lógica de decisão**, com regras condicionais, operadores booleanos e fluxograma.

## Arquivos

| Arquivo | Finalidade |
| --- | --- |
| `motor_decisao.py` | Motor de regras R1–R5, leitura de CSV e geração de alertas JSON |
| `teste_regras.py` | Testes simulados, sem alterar dados reais |
| `Regras_e_Fluxograma.pdf` | Documento do requisito 1 |
| `Evidencia_Testes.png` | Captura do terminal com os cinco testes aprovados |
| `INTEGRACAO.md` | Instruções para incorporar ao repositório principal |

## Regras

- **R1 Normal:** até 10% de folhas doentes e sem persistência.
- **R2 Atenção:** mais de 10% e até 30% de folhas doentes, sem persistência.
- **R3 Crítico:** mais de 30% de folhas doentes, sem persistência.
- **R4 Persistência:** pelo menos uma folha classificada como doente em cada um de três dias corridos no mesmo talhão, desde que R5 não se aplique.
- **R5 Prioridade máxima:** percentual de doentes acima de 30% **AND** persistência de três dias.

O motor usa **AND**, **OR** e **NOT**. A prioridade das regras é R5, R3, R4, R2 e R1. Os alertas são *recomendações*, não acionamentos físicos.

## Executar testes

Requer Python 3.10+; os testes e o motor utilizam apenas a biblioteca padrão.

```bash
python teste_regras.py
```

## Executar com dados reais

Copie `motor_decisao.py` para a raiz do projeto AgroVision, ao lado de `app.py`, e mantenha o arquivo `dados/analises_tratadas.csv` do projeto principal. Depois:

```bash
python motor_decisao.py
```

O resultado é salvo em `dados/alertas.json`. Consulte `INTEGRACAO.md` para ligar o motor ao Streamlit sem sobrescrever o trabalho dos colegas.

## Limitações

Os limiares são didáticos, não parâmetros agronômicos validados. O classificador diferencia apenas **Saudável/Doente**, sem identificar a espécie de praga. A persistência exige observações em três datas corridas consecutivas no mesmo talhão; a ausência de dados em um dia interrompe a sequência. A amostra da Fase 2 é pequena.

## Status

As regras R1–R5 foram aprovadas em testes simulados executados localmente; veja `Evidencia_Testes.png`. A interface Streamlit foi verificada visualmente com os dados disponíveis, mas a integração no repositório consolidado deve ser retestada pelo grupo.
