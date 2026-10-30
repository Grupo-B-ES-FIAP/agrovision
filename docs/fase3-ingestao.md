# Fase 3 | Integração com dados (entrada automatizada)

Este documento descreve o passo 3 da Fase 3: o fluxo que percebe a chegada de
dados novos, processa só o que ainda não foi processado e dispara a automação
sem intervenção manual. As regras (passo 1) estão em
[Fase3_Logica_Decisao/Regras_e_Fluxograma.pdf](../Fase3_Logica_Decisao/Regras_e_Fluxograma.pdf)
e a automação (passo 2) em [fase3-automacao.md](fase3-automacao.md).

## Modelo escolhido: micro-batch

Um processo fica vigiando a pasta `data/entrada`. Quando um arquivo `.csv` ou
`.json` novo aparece, o sistema lê o arquivo, separa os registros que ainda não
conhecia, grava esses registros na camada Bronze e roda o pipeline. O pipeline
chama a automação, que aplica as regras R1 a R5 e grava os alertas e o relatório
de intervenção. O que já foi lido fica em um checkpoint.

### Justificativa

Escolhemos micro-batch porque nenhuma das cinco regras precisa de resposta em
tempo real. Todas trabalham sobre o dia de um talhão: R1, R2 e R3 comparam o
percentual diário de folhas doentes com os limiares de 10% e 30%, e R4 e R5
olham uma janela de três dias seguidos. O percentual do dia só tem sentido
depois que a amostra do dia chegou, e uma regra de três dias não muda se a
decisão sair em um segundo ou em um minuto. Um lote por dia, ou por hora,
atende a latência que as regras exigem. A origem dos dados também é em lote: o
produtor fotografa folhas no campo e as análises são gravadas em arquivos CSV.
Não existe um sensor emitindo eventos contínuos.

Streaming com Apache Kafka seria a escolha se o sistema tivesse uma regra de
reação em minutos, como umidade crítica do solo medida por um sensor a cada
poucos segundos. Para este projeto ele acrescentaria um broker e um contêiner
Docker sem reduzir a latência de nenhuma regra. O micro-batch roda com um
comando, no mesmo ambiente Python do restante do projeto, e o CI consegue
testá-lo. O checkpoint cumpre aqui o papel do offset do consumer group: ele
registra o que já foi lido para que nada seja processado duas vezes.

| Regra | Dado que usa | Latência que exige | Atendida por |
|---|---|---|---|
| R1, R2 | Percentual de doentes do dia | Horas: depende da amostra completa do dia | Micro-batch |
| R3 | Percentual de doentes acima de 30% | Horas: é calculada sobre o dia | Micro-batch |
| R4 | Folha doente em 3 dias seguidos | Dias | Micro-batch |
| R5 | R3 AND R4 | Dias | Micro-batch |

O intervalo de verificação é um parâmetro (`--intervalo`, 5 segundos por
padrão). Em produção bastaria um intervalo de minutos.

## Fluxo

```
Origem                 Ingestão                         Processamento                  Ação
------                 --------                         -------------                  ----
scripts/gerar_lotes.py data/entrada/                    pipeline.executar()
(ou análises do app)   lote_AAAA-MM-DD.csv              Bronze -> Silver -> Gold
        |                      |                                 |
        |   grava .tmp e       v                                 v
        +-- renomeia --> ingestao.processar()          automacao.executar()
                         1. lista arquivos novos          decisao.avaliar()
                            (checkpoint: nome + SHA-256)  regras R1 a R5
                         2. descarta registros                   |
                            já vistos (chave)                    v
                         3. grava os novos na Bronze      data/saida/alertas.json
                         4. atualiza o checkpoint         data/saida/relatorios/
                                |                         log com a linha ALERTA
                                v
                    Sem registro novo? Nada é acionado.
```

O checkpoint fica em `data/saida/checkpoint.json`. A ingestão só chama o
pipeline quando chegou ao menos um registro novo. Por isso um arquivo reenviado
não gera alerta nem relatório repetidos.

## Como o sistema sabe o que já foi processado

O controle tem dois níveis.

1. **Arquivo.** O checkpoint guarda o nome e o SHA-256 de cada arquivo lido. Um
   arquivo com o mesmo nome e o mesmo conteúdo nem é aberto de novo.
2. **Registro.** Cada registro tem a chave `nome_imagem + data + localidade`, a
   mesma que a camada Silver usa para deduplicar. Antes de gravar na Bronze, a
   ingestão compara a chave com as que já estão lá. Um arquivo reenviado com
   outro nome, ou um arquivo que cresceu, entrega só os registros novos.

Casos tratados:

| Situação | Comportamento |
|---|---|
| Arquivo novo | Lido, registros novos entram, pipeline e regras rodam |
| Mesmo arquivo, mesmo conteúdo | Ignorado pelo checkpoint |
| Cópia com outro nome | Lida, 0 registros novos, nada é acionado |
| Arquivo que ganhou linhas | Só as linhas novas entram |
| Arquivo sem as colunas obrigatórias ou JSON quebrado | `rejeitado` no checkpoint, com o motivo. Não é tentado de novo, a menos que o conteúdo mude |
| Arquivo aberto por quem escreve | Fica para o próximo ciclo |
| Arquivo `.tmp` ou em subpasta | Ignorado |
| Processo encerrado e iniciado de novo | O checkpoint evita reler tudo |
| Checkpoint apagado | As chaves na Bronze evitam duplicar registros |
| Botão de limpeza do painel | Apaga o checkpoint junto com as camadas, e os arquivos entram de novo |

O produtor deve gravar em um arquivo `.tmp` e renomear ao terminar, como faz
`scripts/gerar_lotes.py`. Se um arquivo for lido pela metade, a próxima leitura
vê o conteúdo mudado e traz só o que faltava.

## Dicionário de dados

### Registro de entrada

Cada linha de um arquivo em `data/entrada` é uma análise de folha, com as mesmas
colunas da camada Bronze. CSV com ponto e vírgula e UTF-8 com BOM. O JSON aceita
uma lista de objetos ou o formato da exportação do painel, com a chave
`resultados`.

| Campo | Tipo | Unidade | Obrigatório | Exemplo | Descrição |
|---|---|---|---|---|---|
| `nome_imagem` | texto | | sim | `demo_0001.jpg` | Nome do arquivo da imagem analisada |
| `categoria` | texto | | sim | `Saudável` | `Saudável` ou `Doente` |
| `acuracia` | número | % (0 a 100) | sim | `92.54` | Confiança do modelo naquela imagem. Não é a acurácia do modelo |
| `data` | texto | AAAA-MM-DD | sim | `2026-09-01` | Dia da coleta |
| `localidade` | texto | | sim | `Talhão A` | Talhão ou local da coleta |
| `origem` | texto | | não | `Simulado` | `Modelo`, `Modelo (lote)` ou `Simulado` |

Exemplo de registro em CSV:

```
nome_imagem;categoria;acuracia;data;localidade;origem
demo_0001.jpg;Saudável;92.54;2026-09-01;Talhão A;Simulado
```

Exemplo do mesmo registro em JSON:

```json
{
  "nome_imagem": "demo_0001.jpg",
  "categoria": "Saudável",
  "acuracia": 92.54,
  "data": "2026-09-01",
  "localidade": "Talhão A",
  "origem": "Simulado"
}
```

Um arquivo de entrada traz o dia de coleta. O produtor de demonstração entrega
`lote_AAAA-MM-DD.csv`, com 36 registros: 12 imagens por talhão, em 3 talhões.

### Checkpoint

Arquivo: `data/saida/checkpoint.json`. Um objeto com `atualizado_em` e `arquivos`,
que tem uma entrada por arquivo lido.

| Campo | Tipo | Descrição |
|---|---|---|
| `arquivos` | objeto | Chave: nome do arquivo. Valor: o objeto abaixo |
| `atualizado_em` | texto | Data e hora da última gravação do checkpoint |
| `sha256` | texto | Resumo do conteúdo do arquivo quando foi lido |
| `status` | texto | `processado` ou `rejeitado` |
| `linhas` | número | Linhas do arquivo (somente `processado`) |
| `novos` | número | Registros que não eram conhecidos e entraram na Bronze |
| `motivo` | texto | Por que foi rejeitado (somente `rejeitado`) |
| `processado_em` | texto | Data e hora da leitura |

Exemplo:

```json
{
  "arquivos": {
    "lote_2026-09-14.csv": {
      "sha256": "39ad4aec7491abddf0d58b09f4a517e0d19a0a6585afb32a20d6cb6fbc6cfed5",
      "status": "processado",
      "linhas": 36,
      "novos": 36,
      "processado_em": "2026-10-29T21:05:51"
    },
    "lote_2026-09-14_reenvio.csv": {
      "sha256": "39ad4aec7491abddf0d58b09f4a517e0d19a0a6585afb32a20d6cb6fbc6cfed5",
      "status": "processado",
      "linhas": 36,
      "novos": 0,
      "processado_em": "2026-10-29T21:05:57"
    }
  },
  "atualizado_em": "2026-10-29T21:05:58"
}
```

## Evidência de execução

O log completo está em [evidencias/fase3-ingestao-log.txt](evidencias/fase3-ingestao-log.txt).
Ele foi gerado com o monitor ligado em um terminal e o produtor entregando um
lote a cada 3 segundos em outro.

**Passo 1. Liga o monitor.** Ele fica esperando.

```
python -m agrovision.ingestao --demo --intervalo 2
21:05:09 [Ingestao] Vigiando ...\data\entrada\demonstracao a cada 2s. Ctrl+C para encerrar
21:05:09 [Ingestao] Sem arquivos novos. Aguardando
```

**Passo 2. Chegam os dados.** Em outro terminal, `python scripts/gerar_lotes.py
--lotes 14 --intervalo 3` entrega um dia por vez. A cada arquivo, o monitor lê,
roda o pipeline e as regras, sem ninguém tocar nele.

```
21:05:13 [Ingestao] lote_2026-09-01.csv: 36 linha(s), 36 nova(s), 0 ja processada(s)
21:05:13 [Ingestao] 36 registro(s) novo(s). Rodando pipeline e regras de decisao
=== Pipeline AgroVision: Bronze -> Silver -> Gold ===
[Extract] 36 registro(s) lido(s) de analises.csv
[Transform] 36 registro(s) gravado(s) em analises_tratadas.csv
[Load] Indicadores gravados em indicadores.json
[Automacao] 3 decisao(oes) gravada(s) em alertas.json e intervencao_2026-10-29_210513.md
=== Pipeline concluido ===
```

**Passo 3. A ação dispara.** No sexto dia, o Talhão B completa três dias seguidos
com folhas doentes e a regra R4 aciona o alerta. No dia 10, o Talhão C passa de
30% de folhas doentes com persistência, e a regra vira R5. O Talhão B chega a R5
no dia seguinte. Cada alerta aparece no log assim que o lote do dia é processado.

```
21:05:28 [Ingestao] lote_2026-09-06.csv: 36 linha(s), 36 nova(s), 0 ja processada(s)
21:05:28 [Ingestao] ALERTA Talhão B 2026-09-06 16.7% R4 PERSISTÊNCIA: Solicitar avaliação agronômica por persistência de folhas doentes.
...
21:05:41 [Ingestao] ALERTA Talhão C 2026-09-10 50.0% R5 PRIORIDADE MÁXIMA: Solicitar avaliação agronômica prioritária e plano de controle.
21:05:43 [Ingestao] ALERTA Talhão B 2026-09-11 66.7% R5 PRIORIDADE MÁXIMA: Solicitar avaliação agronômica prioritária e plano de controle.
...
21:05:51 [Ingestao] ALERTA Talhão B 2026-09-14 83.3% R5 PRIORIDADE MÁXIMA: Solicitar avaliação agronômica prioritária e plano de controle.
21:05:51 [Ingestao] ALERTA Talhão C 2026-09-14 33.3% R3 CRÍTICO: Investigar possível infestação e intensificar inspeções.
```

**Passo 4. Registros já processados não disparam a ação de novo.** O produtor
copia o último lote (`python scripts/gerar_lotes.py --reenviar`). O arquivo é
lido, mas nenhum registro é novo. O pipeline e a automação não rodam, e nenhum
alerta ou relatório é gerado.

```
21:05:57 [Ingestao] lote_2026-09-14_reenvio.csv: 36 linha(s), 0 nova(s), 36 ja processada(s)
21:05:58 [Ingestao] Nenhum registro novo. Pipeline e automacao nao foram acionados
21:06:00 [Ingestao] Sem arquivos novos. Aguardando
```

**Passo 5. Reinício do processo.** O monitor foi encerrado e iniciado de novo. O
checkpoint evita reler os 15 arquivos.

```
python -m agrovision.ingestao --demo --uma-vez
21:07:08 [Ingestao] Nenhum arquivo novo. 15 arquivo(s) ja constam no checkpoint
```

Ao fim, a Bronze de demonstração tinha 504 registros, 14 dias vezes 36. O
reenvio e o reinício não acrescentaram nenhum.

## No painel

A aba Entrada automatizada do Streamlit mostra o mesmo fluxo:

- Seletor de fonte: Demonstração (`data/entrada/demonstracao`) ou Dados reais (`data/entrada`).
- Chave **Monitorar a pasta automaticamente**: a cada 3 segundos o painel processa os arquivos novos, como o monitor do terminal.
- Botão **Processar a pasta agora**: uma passada manual.
- Botões **Entregar próximo lote**, **Reenviar último lote** e **Reiniciar a demonstração**, que fazem o papel do produtor (só na demonstração).
- Contadores de arquivos na pasta, aguardando leitura, rejeitados e registros na Bronze.
- Tabela dos arquivos com a situação no checkpoint, cartões da situação atual de cada talhão e o log da ingestão.

## Como rodar

Em dois terminais, com o projeto instalado.

```bash
# Terminal 1: liga o monitor da base de demonstração
python -m agrovision.ingestao --demo

# Terminal 2: simula a chegada de dados
python scripts/gerar_lotes.py                    # entrega o próximo dia
python scripts/gerar_lotes.py --lotes 5 --intervalo 10
python scripts/gerar_lotes.py --reenviar         # copia o último lote de novo
python scripts/gerar_lotes.py --reiniciar        # esvazia a pasta de entrada
```

Para os dados reais, rode `python -m agrovision.ingestao` e copie arquivos de
análises para `data/entrada`. Para processar o que houver e sair, use
`--uma-vez`.

A demonstração lê de `data/entrada/demonstracao` e grava em
`data/saida/demonstracao`. Assim os registros simulados nunca entram na base
real, a mesma regra da automação. Os alertas ficam em
`data/saida/demonstracao/alertas.json` e os relatórios em
`data/saida/demonstracao/relatorios/`.

## Código

| Arquivo | Função |
|---|---|
| `src/agrovision/ingestao.py` | Detecção de arquivos novos, checkpoint, deduplicação por registro, monitor e linha de comando |
| `src/agrovision/pipeline.py` | `CHECKPOINT`, `em_saida()` e a limpeza do checkpoint em `limpar()` |
| `src/agrovision/produtor.py` | Produtor: entrega a base de demonstração, um dia por vez |
| `scripts/gerar_lotes.py` | Linha de comando do produtor |
| `src/agrovision/app.py` | Aba Entrada automatizada |
| `tests/test_ingestao.py` | Arquivo novo, repetido, reenviado, rejeitado, checkpoint perdido, monitor e produtor |
| `docs/evidencias/fase3-ingestao-log.txt` | Log da execução descrita acima |

## Limites

- O monitor verifica a pasta a cada intervalo. Ele não reage no instante em que
  o arquivo chega, e não é o caminho certo para uma regra que precise de
  segundos.
- O checkpoint é um arquivo local, para um único monitor. Dois monitores na
  mesma pasta se atrapalhariam.
- A comparação de registros usa `nome_imagem + data + localidade`. Duas folhas
  diferentes com o mesmo nome de arquivo, no mesmo dia e talhão, contam como uma.
- A aba do painel troca as pastas do pipeline durante o processamento (`em_saida`). Foi pensada para um usuário por vez.
- Os dados de demonstração são simulados, e os limiares das regras são
  didáticos, não parâmetros agronômicos validados.
