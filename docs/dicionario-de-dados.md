# Dicionário de dados

Este documento descreve as colunas de cada camada do pipeline. O contrato em
código está em `src/agrovision/esquema.py`.

Todos os arquivos CSV usam ponto e vírgula como separador e codificação
UTF-8 com BOM. O BOM faz o Excel em português abrir o arquivo com as colunas
separadas e os acentos corretos.

## Camada Bronze

Arquivo: `data/saida/analises.csv`

Uma linha por classificação, como ela saiu do modelo. Sem tratamento.

| Coluna | Tipo | Obrigatória | Descrição |
|---|---|---|---|
| `nome_imagem` | texto | sim | Nome do arquivo da imagem, como foi enviado |
| `categoria` | texto | sim | `Saudável` ou `Doente` |
| `acuracia` | número | sim | Confiança do modelo, de 0 a 100. Ver a observação abaixo |
| `data` | texto | sim | Data da coleta, no formato AAAA-MM-DD |
| `localidade` | texto | sim | Talhão ou local da coleta |
| `origem` | texto | não | `Modelo`, `Modelo (lote)` ou `Simulado` |

Observação sobre `acuracia`: a coluna guarda a probabilidade que o modelo
atribui à classe escolhida para aquela imagem. Não é a acurácia do modelo. O
nome vem do enunciado da Fase 1 e foi mantido para os arquivos das duas
entregas continuarem compatíveis. A acurácia do modelo está em
`models/metrics.json`.

## Camada Silver

Arquivo: `data/saida/analises_tratadas.csv`

As mesmas colunas da Bronze, com os tipos validados. É a fonte do painel.

Regras aplicadas, nesta ordem:

1. `data` é convertida para data. Valor que não converte vira nulo.
2. `acuracia` é convertida para número. Valor que não converte vira nulo.
3. A linha é descartada se qualquer coluna obrigatória estiver nula.
4. A linha é descartada se `categoria` não for `Saudável` nem `Doente`.
5. A linha é descartada se outra linha tiver o mesmo `nome_imagem`, a mesma
   `data` e a mesma `localidade`.

A chave de deduplicação inclui data e localidade. A mesma folha fotografada em
outro dia, ou em outro talhão, conta como uma observação nova.

## Camada Gold

Arquivo: `data/saida/indicadores.json`

Indicadores agregados, calculados sobre a camada Silver.

| Campo | Tipo | Descrição |
|---|---|---|
| `gerado_em` | texto | Data e hora da execução do pipeline |
| `total_imagens` | número | Total de análises válidas |
| `percentual_saudaveis` | número | Percentual de folhas saudáveis, com duas casas |
| `percentual_doentes` | número | Percentual de folhas doentes, com duas casas |
| `confianca_media` | número | Média da coluna `acuracia`, com duas casas |
| `por_localidade` | objeto | Contagem de cada categoria por talhão |
| `tendencia_diaria` | objeto | Contagem de cada categoria por dia |
| `impressao_bronze` | texto | Resumo do conteúdo da Bronze nessa execução |
| `mensagem` | texto | Presente somente quando não há dado tratado |

Exemplo:

```json
{
  "gerado_em": "2026-10-01T14:32:10",
  "total_imagens": 17,
  "percentual_saudaveis": 47.06,
  "percentual_doentes": 52.94,
  "confianca_media": 93.74,
  "por_localidade": {
    "Talhão A": { "Doente": 9, "Saudável": 0 },
    "Talhão B": { "Doente": 0, "Saudável": 5 }
  },
  "tendencia_diaria": {
    "2026-09-24": { "Doente": 5, "Saudável": 0 },
    "2026-09-25": { "Doente": 0, "Saudável": 5 }
  }
}
```

## Base de demonstração

Arquivo: `data/exemplos/analises_demo.csv`

Mesmas colunas da Bronze, com `origem` igual a `Simulado`. São 1080 registros,
30 dias, três talhões. Os registros não são inferências do modelo. Eles
existem para o painel ter gráficos antes da primeira análise real.

Para gerar de novo, rode `python scripts/gerar_dados_demo.py`. A semente e a
data final são fixas, logo o arquivo sai sempre igual.

## Métricas do treino

Arquivo: `models/metrics.json`

| Campo | Descrição |
|---|---|
| `treinado_em` | Data e hora do treino |
| `modelo` | Nome do classificador |
| `arvores` | Número de árvores da Random Forest |
| `semente` | Semente do sorteio, fixa para o treino ser reproduzível |
| `proporcao_teste` | Fração das imagens reservada para teste |
| `total_imagens` | Imagens usadas no treino e no teste |
| `n_caracteristicas` | Tamanho do vetor de características |
| `acuracia` | Acurácia no conjunto de teste, de 0 a 1 |
| `relatorio_por_classe` | Precisão, revocação e F1 por categoria |

## Exportações do painel

O painel gera dois arquivos sob demanda, com os registros que estão na tela
depois dos filtros.

- `analises_filtradas.csv`: mesmas colunas da Bronze.
- `analises_filtradas.json`: campos `gerado_em`, `total_imagens` e
  `resultados`, sendo `resultados` a lista de registros.

## Tabelas do pipeline em Spark

O notebook `notebooks/pipeline_spark.py` grava tabelas Delta com os mesmos
dados, mais duas colunas de linhagem na Bronze.

| Tabela | Conteúdo |
|---|---|
| `bronze_analises` | Colunas da Bronze, mais `ingerido_em` e `arquivo_origem` |
| `silver_analises` | Colunas da Silver, com `data` em tipo data |
| `gold_resumo` | Uma linha com os indicadores gerais |
| `gold_por_localidade` | Uma linha por talhão, com total, doentes e percentual |
| `gold_tendencia_diaria` | Uma linha por dia e talhão |
