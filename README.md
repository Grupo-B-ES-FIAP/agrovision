# 🌱 AgroVision

Sistema de reconhecimento de imagens para classificar folhas de tomateiro como **Saudável** ou **Doente**, com dashboard interativo, integração com base de dados (pipeline ETL) e exportação dos resultados em CSV/JSON.

Projeto AgroSmart, **Fase 2**: organização, integração e visualização dos dados.

## Tecnologias utilizadas

- Python
- Streamlit
- OpenCV
- Scikit-learn
- Pandas

## Como executar

Pré-requisito: Python 3.10 ou superior instalado.

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Abra o endereço exibido no terminal (normalmente `http://localhost:8501`).

## Funcionalidades

- **Análise de folhas:** upload de uma ou mais imagens, com local e data da coleta, e classificação automática (Saudável / Doente) com percentual de confiança
- **Dashboard:** imagens analisadas, % saudáveis vs. doentes, confiança média, análises por localidade e evolução por dia, com filtros de período, localidade e classificação
- **Dados simulados** para demonstração, separados das classificações reais do modelo. Ao abrir, o Dashboard mostra os dados reais quando já existem análises salvas, e os simulados quando a base está vazia
- **Pipeline de dados:** executado automaticamente a cada análise; a aba **🔄 Pipeline de dados** mostra as camadas Bronze, Silver e Gold e permite reprocessar
- Exportação dos resultados em **CSV** e **JSON**

## Integração com a base de dados (Fase 2 — item 1.2)

A fonte de dados é um arquivo CSV local (`dados/analises.csv`), atualizado a cada análise feita no aplicativo. O pipeline ETL (ingestão → transformação → visualização) segue a estrutura de camadas Bronze, Silver e Gold, e o **Dashboard consome a camada Silver**:

| Etapa | Camada | Arquivo | O que acontece |
|-------|--------|---------|----------------|
| Ingestão (Extract) | Bronze | `dados/analises.csv` | Resultados brutos da classificação de cada imagem (nome, categoria, confiança, data, localidade, origem) |
| Transformação (Transform) | Silver | `dados/analises_tratadas.csv` | Padronização de tipos, remoção de registros inválidos e duplicados (mesma imagem, data e local). É a fonte do Dashboard |
| Carga (Load) | Gold | `dados/indicadores.json` | Indicadores agregados: total, % saudáveis/doentes, confiança média, totais por localidade e tendência diária |

### Como atualizar os dados

1. Na aba **🔬 Análise de folhas**, envie novas imagens. Elas são classificadas, adicionadas à base (Bronze) e o pipeline roda automaticamente.
2. Na aba **📊 Dashboard**, os gráficos já refletem os novos dados (camada Silver).
3. Na aba **🔄 Pipeline de dados**, é possível conferir cada camada e reprocessar manualmente.

### Uso pela linha de comando (opcional)

```bash
# Importar em lote uma pasta de imagens (pasta, localidade, data opcional)
python importar_novas_imagens.py dataset/doente "Talhão A" 2026-09-10

# Executar o pipeline ETL
python pipeline_dados.py
```

Os dados importados por linha de comando aparecem no Dashboard ao recarregar a página.

## Estrutura do projeto

```
AGROVISION/
├── app.py                      # Aplicação Streamlit (análise, dashboard e pipeline)
├── exportar_dados.py           # Exportação CSV/JSON
├── pipeline_dados.py           # Pipeline ETL (Bronze → Silver → Gold)
├── importar_novas_imagens.py   # Importação em lote via linha de comando
├── treinar_modelo.py           # Treinamento do classificador
├── modelo_folhas.pkl           # Modelo treinado
├── requirements.txt
├── dataset/                    # Imagens de folhas saudáveis e doentes
└── dados/                      # Base de dados e camadas do pipeline
```

## Observações

- O modelo classifica apenas **Saudável/Doente**; não identifica uma doença específica.
- A confiança exibida é a probabilidade estimada pelo modelo, não uma medida de acurácia geral.
- Os dados simulados servem apenas para demonstração e não são inferências do modelo.
- A deduplicação do pipeline considera nome da imagem, data e localidade.

## Integrantes

|      Nome         |   RM   |
|----------------   |--------|
| Alvaro Matos      | 553751 |
| Christian Gonzaga | 553775 |
| Filipe Oliveira   | 552906 |
| Isabela Barcellos | 553746 |

## Vídeos de apresentação

- **Fase 1:** [Assista no YouTube](https://youtu.be/vDnr77sQk-g)
- **Fase 2:** _adicionar o link ou o nome do arquivo do vídeo da Fase 2 aqui_