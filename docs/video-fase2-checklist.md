# Checklist de gravação do vídeo da Fase 2

Passo a passo para gravar a tela, gerar a narração e exportar o vídeo.
Mesmo fluxo da Fase 1.

## Parte 1: preparar o ambiente

1. Abra o PowerShell na pasta do projeto.
2. Rode `.\.venv\Scripts\python.exe -m streamlit run src/agrovision/app.py`.
3. Espere o navegador abrir em `http://localhost:8501`.
4. Deixe a janela preta do terminal aberta. Pode minimizar.
5. Feche as outras abas do navegador. Elas aparecem na gravação.
6. Deixe o navegador em tela cheia, com a tecla F11.

## Parte 2: deixar a tela pronta

1. Abra a aba Painel.
2. Confirme que o botão "Exibir dados de demonstracao" está ligado.
3. Confira os quatro números do topo: 1080, 80,6%, 19,4% e 91,8%.
4. Se os números estiverem diferentes, rode
   `.\.venv\Scripts\python.exe scripts\gerar_dados_demo.py` e recarregue a
   página.
5. Volte para a aba Análise de folhas.

## Parte 3: ensaiar

Faça a sequência inteira uma vez, sem gravar, para pegar o ritmo.

1. Na aba Análise de folhas, escolha o Talhão A e a data de hoje.
2. Envie uma imagem de `data/dataset/saudavel` e uma de
   `data/dataset/doente`.
3. Clique em "Analisar e salvar imagens".
4. Abra os dois resultados e confira a classificação.
5. Vá para a aba Painel e role até o gráfico de evolução por dia.
6. No filtro Localidade, deixe só o Talhão B.
7. Vá para a aba Pipeline de dados e role até o fim.
8. Volte ao painel e clique em "Apagar historico salvo", para limpar as duas
   análises do ensaio.

Se o ensaio correu bem, recarregue a página e comece a gravação de verdade.

## Parte 4: gravar a tela

1. Pressione `Win + Shift + R`. O Snipping Tool abre em modo gravação.
2. Desenhe um retângulo em volta da janela do navegador.
3. Clique em "Iniciar".
4. Siga a ordem dos blocos do
   [roteiro](video-fase2-roteiro.md), sem falar nada.
5. Pause dois segundos em cada tela antes de mudar. Isso dá espaço para a
   narração encaixar.
6. Clique em "Parar" ou pressione `Win + Shift + R` de novo.
7. O vídeo é salvo em MP4, em geral na pasta Vídeos, subpasta Capturas de
   Tela.

Ordem das telas, resumida:

| Ordem | Tela | Tempo alvo |
|---|---|---|
| 1 | Aba Análise de folhas, parada | 22 s |
| 2 | Envio e resultado de duas imagens | 28 s |
| 3 | Painel, quatro indicadores no topo | 25 s |
| 4 | Gráfico Análises por localidade | 30 s |
| 5 | Gráfico Evolução por dia, filtrado no Talhão B | 35 s |
| 6 | Aba Pipeline de dados, três camadas | 30 s |
| 7 | Tela parada para o encerramento | 15 s |

## Parte 5: narração e montagem no Clipchamp

1. Abra o Clipchamp pelo Menu Iniciar.
2. Crie um projeto novo e importe o MP4 que você gravou.
3. Abra a ferramenta de texto para fala no menu lateral.
4. Abra [video-fase2-narracao.txt](video-fase2-narracao.txt).
5. Copie um parágrafo por vez e gere o áudio de cada um. Sete parágrafos, um
   por bloco do roteiro.
6. Escolha uma voz em português e mantenha a mesma em todos.
7. Arraste cada faixa de áudio para o tempo indicado no roteiro.
8. Dê play e confira se a fala bate com a tela. Ajuste arrastando as bordas.
9. Confira a duração total. Precisa ficar entre 2 e 4 minutos.
10. Clique em "Exportar" e salve o MP4 final.

## Parte 6: publicar

1. Envie o vídeo para o YouTube, como não listado, igual ao da Fase 1.
2. Copie o link.
3. No `README.md`, troque a linha "Fase 2: a publicar" pelo link.
4. Faça um commit com essa mudança.
5. Mande o link para o grupo antes da entrega.

## Problemas comuns

**O navegador não abre.** Abra manualmente e digite `localhost:8501`.

**Os números do painel estão diferentes do roteiro.** O botão de dados de
demonstração está desligado. Ligue e recarregue a página.

**A aba Painel mostra aviso de que não há análises.** A base real está vazia e
o botão de demonstração está desligado. Ligue o botão.

**O vídeo passou de 4 minutos.** Corte as pausas entre as telas. O roteiro tem
3 minutos de narração, logo a sobra está no vídeo.
