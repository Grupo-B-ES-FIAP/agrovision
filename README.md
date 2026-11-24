# AgroVision

[![CI](https://github.com/Grupo-B-ES-FIAP/agrovision/actions/workflows/ci.yml/badge.svg)](https://github.com/Grupo-B-ES-FIAP/agrovision/actions/workflows/ci.yml)

Classificação de folhas de tomateiro por visão computacional, com painel
analítico e pipeline de dados.

O produtor fotografa folhas no campo. O AgroVision diz quais estão saudáveis e
quais apresentam sinais de doença. Cada análise fica guardada com data e
talhão. O painel mostra onde o problema está crescendo. Com isso, a aplicação
de defensivo vai para o talhão que precisa, e não para a fazenda inteira.

Projeto acadêmico AgroSmart, FIAP. Quatro fases: visão computacional na Fase 1,
organização e visualização dos dados na Fase 2, regras de decisão, automação e
entrada automatizada de dados na Fase 3, e streaming de eventos, contêineres e
modelo de negócio na Fase 4.

![Painel do AgroVision](docs/img/painel.jpg)

## O que o sistema faz

| Aba | Função |
|---|---|
| Análise de folhas | Recebe uma ou mais imagens, com o local e a data da coleta. Classifica cada folha como saudável ou doente, com o percentual de confiança |
| Painel | Imagens analisadas, percentual de saudáveis e doentes, confiança média, contagem por talhão e evolução por dia. Filtros de período, local e classificação |
| Inteligência no campo | Aplica as regras de decisão da Fase 3 por talhão e dia. Mostra o nível atual de cada talhão, a ação recomendada, o histórico de decisões e gera o relatório de intervenção |
| Entrada automatizada | Vigia a pasta de entrada, lê só os registros novos e dispara o pipeline e as regras. Mostra os arquivos, o checkpoint, os alertas e o log. Na demonstração, entrega e reenvia lotes |
| Streaming | Eventos de sensores e folhas chegando em tempo real pelo broker Kafka. Mostra o fluxo, os alertas, os eventos rejeitados por segurança e roda uma simulação sem Docker |
| Arquitetura e Docker | Diagrama dos contêineres, serviços, estado do broker e comandos |
| Modelo de negócio | Business Model Canvas do AgroSmart, Canvas da Proposta de Valor, hipóteses a validar e concorrência |
| Pipeline de dados | Mostra as três camadas de dados, permite reprocessar e exportar os resultados em CSV e JSON |

## Como rodar

Pré-requisito: Python 3.10 ou superior.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m streamlit run src/agrovision/app.py
```

### Linux e macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
streamlit run src/agrovision/app.py
```

Abra o endereço que o terminal mostrar, em geral `http://localhost:8501`.

Na primeira vez, a base está vazia e o painel abre com dados de demonstração.
Para ver dados reais, analise imagens na primeira aba. Há 200 imagens de
exemplo em `data/dataset/`.

## Como funciona

```
Imagem da folha
      |
      v
OpenCV: redimensiona para 128x128, converte para HSV
      |
      v
Histograma de 32 faixas por canal  ->  vetor de 96 números
      |
      v
Random Forest (scikit-learn)  ->  Saudável ou Doente + confiança
      |
      v
Camada Bronze (CSV)  ->  Silver (validada)  ->  Gold (indicadores)
                                 |
                                 v
                         Painel Streamlit
```

Matiz, saturação e brilho separam bem folha verde de folha com mancha
necrosada, e o histograma descreve a imagem sem depender do enquadramento da
foto. O detalhe de cada camada está em [docs/arquitetura.md](docs/arquitetura.md).

O pipeline em pandas é o caminho padrão, porque roda local e sem conta em
nuvem. Para escala, o mesmo fluxo existe em Apache Spark no notebook
[notebooks/pipeline_spark.py](notebooks/pipeline_spark.py), com tabelas Delta e
agendamento por Job no Databricks.

## Fase 3: decisão, automação e entrada de dados

As regras de decisão estão em
[Fase3_Logica_Decisao/Regras_e_Fluxograma.pdf](Fase3_Logica_Decisao/Regras_e_Fluxograma.pdf).
A cada análise nova, o pipeline aplica as regras e grava
`data/saida/alertas.json` e um relatório de intervenção em
`data/saida/relatorios/`. O funcionamento e as capturas de tela estão em
[docs/fase3-automacao.md](docs/fase3-automacao.md).

Os dados novos entram sem intervenção manual. Um monitor vigia a pasta
`data/entrada`, lê só os registros que ainda não foram vistos e dispara o
pipeline e as regras. O modelo é micro-batch, com checkpoint do que já foi lido.
A justificativa, o diagrama, o dicionário de dados e o log de execução estão em
[docs/fase3-ingestao.md](docs/fase3-ingestao.md).

![Aba Inteligência no campo](docs/img/fase3-situacao-demo.png)

## Fase 4: streaming de dados

Sensores de solo e câmeras enviam eventos a um broker Kafka (Redpanda). Cada
evento é assinado, validado e só então entra no pipeline e nas regras de
decisão. Eventos adulterados, repetidos ou de dispositivos desconhecidos vão
para um tópico de rejeitados. O diagrama, os tópicos, os controles de segurança
e o passo a passo estão em [docs/fase4-streaming.md](docs/fase4-streaming.md).

```powershell
docker compose -f streaming/broker.yml up -d
python -m agrovision.streaming.transporte          # cria os tópicos
python -m agrovision.streaming.consumidor --demo   # terminal A
python -m agrovision.streaming.produtor --ticks 32 --intervalo 1 --ataque-a-cada 8   # terminal B
```

Sem Docker, a aba **Streaming** do painel tem o botão **Simular**, que roda o
fluxo completo em memória.

Para encerrar o broker: `docker compose -f streaming/broker.yml down`.

## Fase 4: contêineres

Um único comando sobe o broker, o produtor, o consumidor e o painel:

```bash
docker compose up --build        # sobe tudo
docker compose ps                # estado dos serviços
docker compose down -v           # derruba e apaga os dados
```

Painel em http://localhost:8501 (aba **Streaming**) e console do broker em
http://localhost:8080. O compose completo e o `streaming/broker.yml` usam as mesmas
portas, então derrube um antes de subir o outro. Serviços, decisões do Dockerfile
e o que mostrar nos prints estão em [docs/fase4-docker.md](docs/fase4-docker.md).

## Fase 4: modelo de negócio

O AgroSmart estruturado com o Business Model Canvas e o Canvas da Proposta de
Valor, com as hipóteses a validar e a concorrência. O que depende do mercado
está marcado como hipótese, sem números inventados. Fica na aba
**Modelo de negócio** do painel.

![Business Model Canvas na aba Modelo de negócio](docs/img/canvas-agrosmart.png)

## Desempenho do modelo

| Métrica | Valor |
|---|---|
| Acurácia no conjunto de teste | 95,00% |
| Imagens de treino | 160 |
| Imagens de teste | 40 |
| Classificador | Random Forest, 200 árvores, semente 42 |

Os números saem de `models/metrics.json`, gravado pelo próprio treino. Para
reproduzir, rode `python scripts/treinar_modelo.py`. A semente é fixa, logo o
resultado é sempre o mesmo.

## Limites do protótipo

- O modelo classifica saudável ou doente. Não identifica a doença específica.
- Foi treinado em uma cultura, o tomateiro, com imagens de pinta-preta.
- A confiança exibida é a probabilidade que o modelo dá àquela imagem. Não é a
  acurácia do modelo.
- O desempenho cai com foto mal iluminada ou com fundo poluído, porque o vetor
  de características descreve cor.
- A base de demonstração é simulada e serve para apresentar o painel. Os
  registros simulados nunca entram na base real.

## Estrutura do projeto

```
src/agrovision/      aplicativo, pipeline ETL, visão computacional, regras, automação e ingestão
src/agrovision/streaming/  eventos, produtor, consumidor e transporte Kafka (Fase 4)
streaming/           tópicos do broker e compose só do broker
Dockerfile           imagem única do painel, produtor e consumidor
docker-compose.yml   ambiente completo em contêineres
Fase3_Logica_Decisao/  regras de decisão da Fase 3 (PDF e fluxograma)
scripts/             treino, importação em lote, base de demonstração e produtor de lotes
tests/               testes do pipeline, da visão, do modelo, da exportação, das regras e da ingestão
notebooks/           pipeline em Apache Spark para o Databricks
data/dataset/        200 imagens de folhas, saudáveis e doentes
data/exemplos/       base de demonstração do painel
data/entrada/        arquivos que chegam para a ingestão, gerados em tempo de execução
data/saida/          camadas Bronze, Silver e Gold e checkpoint, gerados em tempo de execução
models/              modelo treinado e métricas do treino
docs/                arquitetura, dicionário de dados e material dos vídeos
```

## Linha de comando

```bash
# Classificar uma pasta de imagens de uma vez
python scripts/importar_imagens.py data/dataset/doente "Talhão A" 2026-09-10

# Rodar o pipeline ETL (inclui a automação da Fase 3)
python -m agrovision.pipeline

# Gerar alertas e relatório de intervenção
python -m agrovision.automacao          # dados reais
python -m agrovision.automacao --demo   # base de demonstração

# Ingestão automatizada: vigia data/entrada e processa só o que é novo
python -m agrovision.ingestao --demo    # base de demonstração (outro terminal:)
python scripts/gerar_lotes.py --lotes 5 --intervalo 10

# Streaming (Fase 4): simulação completa sem broker
python -m agrovision.streaming.demo --ticks 32 --ataque-a-cada 8

# Treinar o modelo de novo
python scripts/treinar_modelo.py

# Gerar a base de demonstração
python scripts/gerar_dados_demo.py
```

## Testes

```bash
ruff check .
pytest
```

O GitHub Actions roda os dois comandos em cada push e em cada pull request.

## Documentação

- [Arquitetura e camadas de dados](docs/arquitetura.md)
- [Fase 3: automação das ações](docs/fase3-automacao.md)
- [Fase 3: integração com dados (entrada automatizada)](docs/fase3-ingestao.md)
- [Fase 4: pipeline com streaming](docs/fase4-streaming.md)
- [Fase 4: containerização com Docker](docs/fase4-docker.md)
- [Fase 4: roteiro do vídeo](docs/video-fase4-roteiro.md)
- [Dicionário de dados](docs/dicionario-de-dados.md)
- [Origem do dataset](data/README.md)
- [Relatório técnico da Fase 1](docs/relatorio-tecnico-fase1.pdf)

## Vídeos de apresentação

- Fase 1: https://youtu.be/vDnr77sQk-g
- Fase 2: a publicar
- Fase 4: a publicar

## Histórico das sprints

A entrega da Fase 1 está preservada na tag `v1.0-fase1`, exatamente como foi
avaliada. Para ver aquele código:

```bash
git checkout v1.0-fase1
```

## Integrantes

| Nome | RM |
|---|---|
| Alvaro Matos | 553751 |
| Christian Gonzaga | 553775 |
| Filipe Oliveira | 552906 |
| Isabela Barcellos | 553746 |

## Licença

Código sob licença MIT, em [LICENSE](LICENSE). As imagens de
`data/dataset/` têm origem e condições próprias, descritas em
[data/README.md](data/README.md).
