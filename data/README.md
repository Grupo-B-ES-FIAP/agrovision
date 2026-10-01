# Dados do projeto

## `dataset/`

200 imagens de folhas de tomateiro, 100 saudáveis e 100 com sinais de doença.
São uma amostra do PlantVillage, um conjunto público de imagens de folhas de
plantas com e sem doença.

- Origem: https://github.com/spMohanty/PlantVillage-Dataset
- As imagens saudáveis vêm da classe `Tomato___healthy`.
- As imagens doentes vêm da classe `Tomato___Early_blight`, a pinta-preta.

### Condições de uso

O repositório de origem não declara licença. Ele pede a citação do artigo
abaixo para quem usa o conjunto:

> Mohanty, S. P., Hughes, D. P., Salathé, M. (2016). Using deep learning for
> image-based plant disease detection. Frontiers in Plant Science, 7:1419.

Sem licença declarada, o uso aqui é acadêmico e a citação acima acompanha o
projeto. Antes de qualquer uso comercial, consulte os autores do conjunto.

A licença MIT do repositório cobre o código deste projeto. Ela não cobre as
imagens desta pasta.

## `exemplos/`

`analises_demo.csv` é a base de demonstração do painel. São 1080 registros
gerados por `scripts/gerar_dados_demo.py`, com semente fixa.

Os registros não são inferências do modelo. A coluna `origem` marca
`Simulado`. Eles existem para o painel ter gráficos antes da primeira análise
real, e para o vídeo de apresentação ter uma história de campo para mostrar.

## `saida/`

Camadas Bronze, Silver e Gold, geradas em tempo de execução. Esta pasta não
entra no controle de versão, porque o conteúdo depende das imagens que cada
pessoa analisa.

As colunas de cada camada estão em
[docs/dicionario-de-dados.md](../docs/dicionario-de-dados.md).
