# Roteiro do vídeo da Fase 2

Duração alvo: 3 minutos. O limite do enunciado é de 2 a 4 minutos.

Formato igual ao da Fase 1: você grava a tela sem falar, depois gera a
narração com voz de IA no Clipchamp e encaixa cada bloco no tempo indicado.

O texto puro da narração está em
[video-fase2-narracao.txt](video-fase2-narracao.txt). O passo a passo da
gravação está em [video-fase2-checklist.md](video-fase2-checklist.md).

Antes de gravar, prepare a tela conforme o checklist. O painel precisa estar
com os dados de demonstração ligados.

---

## 0:00 a 0:22 — Abertura

Tela: aba Análise de folhas, parada.

> Esse é o AgroVision, na Fase 2. Eu sou o Alvaro, e desenvolvi com o
> Christian, o Filipe e a Isabela. Na Fase 1 o sistema classificava uma folha
> de tomateiro como saudável ou doente. Agora, ele organiza essas
> classificações em uma base de dados e mostra em um painel onde está o
> problema na lavoura.

## 0:22 a 0:50 — De onde vem o dado

Tela: subir duas imagens na aba Análise de folhas, uma saudável e uma doente.
Mostrar o resultado de cada uma.

> O dado nasce aqui. O agricultor escolhe o talhão e a data da coleta, e envia
> as fotos. O modelo classifica cada folha e mostra a confiança da previsão.
> Repare que o local e a data entram junto com o resultado. É isso que depois
> permite responder onde e quando o problema apareceu.

## 0:50 a 1:15 — Os números do painel

Tela: aba Painel, com os quatro indicadores no topo visíveis.

> No painel, os quatro indicadores do topo dão a leitura geral. São mil e
> oitenta imagens analisadas em trinta dias. Dessas, oitenta vírgula seis por
> cento são folhas saudáveis. A confiança média do modelo é de noventa e um
> vírgula oito por cento. Esse último número importa. Ele diz o quanto dá para
> confiar no resto do painel.

## 1:15 a 1:45 — Onde está o problema

Tela: gráfico Análises por localidade. Passe o mouse sobre a barra do
Talhão B.

> Essa quebra por talhão é a primeira decisão prática. O Talhão A tem seis por
> cento de folhas doentes. O Talhão C tem dezesseis. O Talhão B tem trinta e
> cinco. A média da fazenda esconderia isso. Com o painel, o produtor
> vê que o problema está concentrado em um talhão, e aplica defensivo só ali.
> Isso economiza produto, economiza hora de máquina e reduz o resíduo no
> restante da lavoura.

## 1:45 a 2:20 — Quando agir

Tela: gráfico Evolução por dia. Filtre a localidade para só o Talhão B, para
a curva ficar limpa.

> A segunda decisão é de tempo. Filtrei só o Talhão B. A linha vermelha mostra
> o foco de praga crescendo a partir do dia onze. O pico é no dia dezenove.
> Depois da aplicação de defensivo, ela cai e volta ao normal no fim do mês.
> Uma linha subindo assim é um alerta antes da perda acontecer. O produtor não
> precisa esperar a lavoura mostrar dano para agir.

## 2:20 a 2:50 — A base por trás do painel

Tela: aba Pipeline de dados. Mostrar os três blocos, Bronze, Silver e Gold.

> Tudo isso vem de um pipeline de três camadas. A Bronze guarda cada
> classificação como ela saiu do modelo. A Silver valida os tipos e remove
> registro inválido e repetido, e é a camada que alimenta o painel. A Gold
> guarda os indicadores prontos. Cada análise nova roda esse fluxo
> automaticamente. E os resultados saem em CSV ou JSON, para abrir no Excel ou
> alimentar outro sistema.

## 2:50 a 3:05 — Encerramento

Tela: parada na aba Pipeline de dados, ou de volta ao painel.

> O projeto também tem o mesmo pipeline escrito em Apache Spark, para rodar no
> Databricks quando o volume crescer. Continua sendo um protótipo. Uma
> cultura, uma doença, e sensível à qualidade da foto. Mas já mostra o que o
> AgroSmart propõe. Usar o dado do campo para decidir onde agir, em vez de
> agir em tudo por precaução. Valeu.

---

## Checagem antes de exportar

- A duração total está entre 2 e 4 minutos.
- Os quatro indicadores do topo aparecem legíveis em algum momento.
- O gráfico por talhão aparece.
- O gráfico de evolução por dia aparece, filtrado no Talhão B.
- A aba Pipeline de dados aparece com as três camadas.
- A narração cita pelo menos duas decisões do agricultor: onde aplicar e
  quando aplicar.

## Números citados na narração

Confira estes valores na tela antes de gravar. Eles vêm da base de
demonstração, que é fixa.

| Indicador | Valor |
|---|---|
| Imagens analisadas | 1080 |
| Saudáveis | 80,6% |
| Doentes | 19,4% |
| Confiança média | 91,8% |
| Talhão A, folhas doentes | 6,4% |
| Talhão B, folhas doentes | 35,3% |
| Talhão C, folhas doentes | 16,7% |
| Pico do foco no Talhão B | 19 de setembro |
