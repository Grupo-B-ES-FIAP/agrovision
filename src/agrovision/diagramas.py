#Diagramas da Fase 4 em Graphviz (DOT), desenhados direto no painel

CONFIG = (
    'rankdir=LR; bgcolor="transparent"; '
    'node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, '
    'color="#4A5568"]; '
    'edge [fontname="Helvetica", fontsize=9, color="#4A5568"];'
)

PIPELINE_STREAMING = f"""
digraph G {{
  {CONFIG}
  sensor  [label="Sensores de solo\\n(umidade, temperatura)", fillcolor="#FEF3C7"];
  camera  [label="Camera + modelo\\nfolha: saudavel ou doente", fillcolor="#FEF3C7"];
  prod    [label="Produtor\\nassina cada evento (HMAC)", fillcolor="#DBEAFE"];
  broker  [label="Redpanda (Kafka)\\ntopicos sensores e analises", fillcolor="#C7D2FE"];
  cons    [label="Consumidor\\nvalida, remove duplicados", fillcolor="#DBEAFE"];
  rej     [label="Topico rejeitados\\n(motivo da rejeicao)", fillcolor="#FECACA"];
  sens    [label="Limites de campo\\nS1 umidade, S2 calor", fillcolor="#D1FAE5"];
  etl     [label="Pipeline ETL\\nBronze, Silver, Gold", fillcolor="#D1FAE5"];
  regras  [label="Regras R1 a R5\\n(Fase 3)", fillcolor="#D1FAE5"];
  alertas [label="Topico alertas", fillcolor="#C7D2FE"];
  painel  [label="Painel Streamlit", fillcolor="#FBCFE8"];

  sensor -> prod; camera -> prod; prod -> broker [label="eventos"];
  broker -> cons; cons -> rej [label="invalido ou repetido"];
  cons -> sens [label="sensor"]; cons -> etl [label="analise"]; etl -> regras;
  sens -> alertas; regras -> alertas; alertas -> painel; rej -> painel;
}}
"""

ARQUITETURA_DOCKER = f"""
digraph G {{
  {CONFIG}
  compound=true;
  usuario [label="Navegador\\nlocalhost:8501 e :8080", shape=ellipse, fillcolor="#FBCFE8"];
  subgraph cluster_compose {{
    label="docker compose (rede agrovision)"; style="rounded,dashed"; color="#718096";
    fontname="Helvetica";
    redpanda [label="redpanda\\nbroker Kafka", fillcolor="#C7D2FE"];
    console  [label="console\\ninterface dos topicos :8080", fillcolor="#C7D2FE"];
    topicos  [label="topicos\\ncria os topicos e encerra", fillcolor="#E2E8F0"];
    produtor [label="produtor\\nsimula sensores e folhas", fillcolor="#DBEAFE"];
    consumidor [label="consumidor\\nvalida e roda o pipeline", fillcolor="#DBEAFE"];
    dashboard [label="dashboard\\nStreamlit :8501", fillcolor="#FBCFE8"];
    volume [label="volume saida\\ndata/saida", shape=cylinder, fillcolor="#FEF3C7"];
  }}
  topicos -> redpanda [label="cria"]; produtor -> redpanda [label="publica"];
  redpanda -> consumidor [label="entrega"]; console -> redpanda [label="le"];
  consumidor -> volume [label="grava"]; volume -> dashboard [label="le"];
  usuario -> dashboard; usuario -> console;
}}
"""
