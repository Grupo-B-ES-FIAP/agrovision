# Integração no projeto principal

O motor de decisões desta pasta foi integrado ao pacote `agrovision`. A tabela mostra onde cada parte ficou.

| Antes (esta pasta) | Depois (repositório principal) |
| --- | --- |
| `motor_decisao.py`, função `avaliar()` | `src/agrovision/decisao.py`, função `avaliar()` |
| `motor_decisao.py`, função `executar()` | `src/agrovision/automacao.py`, função `executar()` |
| `teste_regras.py` | `tests/test_decisao.py`, em pytest |
| `dados/analises_tratadas.csv` | `data/saida/analises_tratadas.csv` (camada Silver) |
| `dados/alertas.json` | `data/saida/alertas.json` |
| Aba do Streamlit sugerida | Aba Inteligência no campo em `src/agrovision/app.py` |

## O que mudou na integração

1. O motor usa os nomes de coluna de `src/agrovision/esquema.py`, os mesmos do pipeline e do painel.
2. Os limiares viraram constantes: `LIMIAR_CRITICO = 30`, `LIMIAR_ATENCAO = 10` e `DIAS_PERSISTENCIA = 3`.
3. A lógica das regras e a ordem de prioridade (R5, R3, R4, R2, R1) não mudaram.
4. O pipeline chama a automação ao fim de cada carga. Ver [docs/fase3-automacao.md](../docs/fase3-automacao.md).

## Contrato de saída

`automacao.executar()` grava `alertas.json` com `gerado_em`, `fonte`, `criterios_experimentais` e `alertas`. Cada alerta contém `data`, `total`, `doentes`, `percentual_doentes`, `talhao`, `nivel`, `regra`, `persistencia_3_dias`, `controle_recomendado`, `situacao_normal` e `recomendacao`.

## Atenção

Os arquivos de `data/saida/` são gerados em tempo de execução e ficam fora do Git. O módulo não identifica pragas específicas nem executa controles físicos.
