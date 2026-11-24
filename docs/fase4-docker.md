# Fase 4 | Containerização da solução

Este documento descreve o item 2 da Fase 4: a solução empacotada em contêineres
Docker e orquestrada por um `docker-compose.yml`. Um único comando sobe o broker
de streaming, o produtor, o consumidor e o painel.

## Arquitetura

```mermaid
flowchart LR
    U[Navegador] -->|:8501| D[dashboard<br/>Streamlit]
    U -->|:8080| C[console<br/>interface do broker]
    T[topicos<br/>cria os tópicos e encerra] -->|cria| R
    P[produtor<br/>simula sensores e câmeras] -->|publica| R[(redpanda<br/>broker Kafka)]
    R -->|entrega| K[consumidor<br/>valida, pipeline e regras]
    C -->|lê| R
    K -->|grava| V[(volume saida<br/>data/saida)]
    V -->|lê| D
```

O mesmo diagrama aparece no painel, na aba **🐳 Arquitetura e Docker**, junto
com o estado do broker.

## Serviços

| Serviço | Imagem | Porta | Função |
|---|---|---|---|
| `redpanda` | `redpandadata/redpanda` | 9092 | Broker Kafka. Dois endereços: `redpanda:29092` entre contêineres e `localhost:9092` para o seu computador |
| `console` | `redpandadata/console` | 8080 | Interface web para ver tópicos e mensagens |
| `topicos` | `agrovision:fase4` | | Tarefa única: cria os quatro tópicos e encerra |
| `produtor` | `agrovision:fase4` | | Simula sensores e câmeras e injeta um ataque a cada 8 rodadas |
| `consumidor` | `agrovision:fase4` | | Valida os eventos, grava na Bronze, roda pipeline e regras, publica alertas |
| `dashboard` | `agrovision:fase4` | 8501 | Painel Streamlit |

O painel, o produtor, o consumidor e a criação dos tópicos usam **a mesma imagem**
(`agrovision:fase4`), cada um com um comando diferente. Assim há um só Dockerfile
para manter e o código dos quatro nunca fica fora de sincronia.

## Como executar

Pré-requisito: Docker Desktop em execução.

```powershell
docker compose up --build        # primeira vez: constrói a imagem (alguns minutos)
```

Depois:

- Painel: http://localhost:8501, aba **📡 Streaming**
- Console do broker: http://localhost:8080, menu **Topics**

Comandos úteis:

```powershell
docker compose ps                    # estado dos serviços
docker compose logs -f consumidor    # acompanha a validação e os alertas
docker compose restart produtor      # repete a simulação
docker compose down                  # derruba, mantendo os dados
docker compose down -v               # derruba e apaga os dados
```

O produtor roda 40 rodadas (10 dias simulados) e encerra. Em seguida o painel
continua mostrando o resultado. Para outra execução, `docker compose restart produtor`.

## Decisões do Dockerfile

| Decisão | Motivo |
|---|---|
| Base `python:3.11-slim` | Mesma versão do CI, imagem enxuta |
| Dependências copiadas antes do código | Mexer no código não refaz a camada de instalação |
| `pip install -e .` | O projeto acha `models/` e `data/` a partir de `/app`, como fora do contêiner |
| Usuário `agro` sem privilégios | O processo não roda como root |
| `.dockerignore` sem `data/dataset`, testes e docs | A imagem leva só o que executa (o dataset de treino tem 200 imagens que o painel não usa) |
| Healthcheck só no `dashboard` | Produtor e consumidor não têm porta HTTP |

## Dados e configuração

- **Volume `saida`**: o consumidor grava nele e o painel lê. É o que permite os
  dois contêineres compartilharem Bronze, Silver, Gold, alertas e o estado do streaming.
- **`KAFKA_BROKER`**: endereço do broker, `redpanda:29092` dentro da rede do compose.
- **`AGROVISION_SEGREDO`**: chave das assinaturas dos eventos. O padrão serve só
  para a demonstração. Para trocar, defina a variável antes de subir:
  `$env:AGROVISION_SEGREDO = "outra-chave"; docker compose up`.
- **Ordem de partida**: `depends_on` com condições. Os tópicos só são criados
  quando o broker está saudável, e produtor e consumidor só iniciam depois dos tópicos.

## Prints

Estado dos serviços (`docker compose ps -a`). O `topicos` e o `produtor` terminam com
código 0 por serem tarefas finitas, e o `redpanda` e o `dashboard` ficam saudáveis:

![docker compose ps](img/fase4-docker-ps.png)

Painel rodando no contêiner, aba **Arquitetura e Docker**, com o broker acessível:

![Aba Arquitetura e Docker](img/fase4-docker-painel.png)

Console do broker em http://localhost:8080, com os quatro tópicos criados:

![Tópicos no console do broker](img/fase4-kafka-topicos.png)

## Resultado do teste

Executado com `docker compose up --build`:

- Os seis serviços sobem na ordem correta. `topicos` encerra com código 0.
- O broker responde como saudável e o painel responde `200` em `/_stcore/health`.
- O consumidor valida os eventos, roda o pipeline e emite alertas (R3, R4, R5, S1).
- Os ataques do produtor são rejeitados com motivo.
