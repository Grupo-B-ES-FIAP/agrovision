# Databricks notebook source
# MAGIC %md
# MAGIC # AgroVision: pipeline de dados com Apache Spark
# MAGIC
# MAGIC Este notebook e a versao em Apache Spark do pipeline que roda em pandas
# MAGIC no aplicativo. As duas versoes produzem os mesmos indicadores.
# MAGIC
# MAGIC | Caminho | Ferramenta | Quando usar |
# MAGIC |---|---|---|
# MAGIC | `src/agrovision/pipeline.py` | pandas | Uso local. Centenas ou milhares de analises. Roda sem conta em nuvem. |
# MAGIC | Este notebook | Apache Spark no Databricks | Escala. Milhoes de analises, varias fazendas, execucao agendada. |
# MAGIC
# MAGIC Arquitetura em tres camadas, o padrao medalhao:
# MAGIC
# MAGIC 1. **Bronze**: ingestao do CSV que o aplicativo gera, sem tratamento.
# MAGIC 2. **Silver**: tipos validados, registros invalidos e duplicados removidos.
# MAGIC 3. **Gold**: tabelas agregadas, prontas para o painel.
# MAGIC
# MAGIC ## Como rodar na Databricks Free Edition
# MAGIC
# MAGIC 1. Crie um volume para os arquivos de entrada.
# MAGIC 2. Envie `data/saida/analises.csv` para esse volume.
# MAGIC 3. Importe este arquivo pelo menu Workspace, opcao Import.
# MAGIC 4. Ajuste os tres widgets no topo do notebook.
# MAGIC 5. Rode todas as celulas.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Parametros
# MAGIC
# MAGIC Os widgets deixam o notebook rodar em qualquer catalogo e volume, sem
# MAGIC editar codigo.

# COMMAND ----------

dbutils.widgets.text("catalogo", "workspace", "Catalogo")
dbutils.widgets.text("esquema", "agrovision", "Esquema")
dbutils.widgets.text(
    "arquivo_entrada",
    "/Volumes/workspace/agrovision/entrada/analises.csv",
    "CSV de entrada",
)

CATALOGO = dbutils.widgets.get("catalogo")
ESQUEMA = dbutils.widgets.get("esquema")
ARQUIVO_ENTRADA = dbutils.widgets.get("arquivo_entrada")

BRONZE = f"{CATALOGO}.{ESQUEMA}.bronze_analises"
SILVER = f"{CATALOGO}.{ESQUEMA}.silver_analises"
GOLD_RESUMO = f"{CATALOGO}.{ESQUEMA}.gold_resumo"
GOLD_LOCALIDADE = f"{CATALOGO}.{ESQUEMA}.gold_por_localidade"
GOLD_TENDENCIA = f"{CATALOGO}.{ESQUEMA}.gold_tendencia_diaria"

spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOGO}.{ESQUEMA}")
print(f"Entrada: {ARQUIVO_ENTRADA}")
print(f"Tabelas: {BRONZE}, {SILVER}, {GOLD_RESUMO}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Bronze: ingestao
# MAGIC
# MAGIC O esquema e declarado, nao inferido. Inferir esquema custa uma leitura
# MAGIC extra do arquivo e deixa o tipo de cada coluna a merce dos dados do dia.
# MAGIC Com o esquema declarado, um valor fora do tipo chega como nulo e a camada
# MAGIC Silver o descarta.

# COMMAND ----------

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType

ESQUEMA_ANALISES = StructType(
    [
        StructField("nome_imagem", StringType(), nullable=False),
        StructField("categoria", StringType(), nullable=False),
        StructField("acuracia", DoubleType(), nullable=True),
        StructField("data", StringType(), nullable=True),
        StructField("localidade", StringType(), nullable=True),
        StructField("origem", StringType(), nullable=True),
    ]
)

bronze = (
    spark.read.format("csv")
    .option("header", True)
    .option("sep", ";")
    .option("encoding", "UTF-8")
    .schema(ESQUEMA_ANALISES)
    .load(ARQUIVO_ENTRADA)
    .withColumn("ingerido_em", F.current_timestamp())
    .withColumn("arquivo_origem", F.input_file_name())
)

bronze.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(BRONZE)
print(f"Bronze: {spark.table(BRONZE).count()} registros")
display(spark.table(BRONZE).limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Silver: transformacao
# MAGIC
# MAGIC Tres regras, as mesmas da versao em pandas:
# MAGIC
# MAGIC 1. Converter a data e a confianca. Valor que nao converte vira nulo.
# MAGIC 2. Descartar registro sem campo obrigatorio ou com categoria fora do
# MAGIC    contrato. As categorias validas sao `Saudável` e `Doente`.
# MAGIC 3. Descartar duplicata de nome da imagem, data e localidade. A mesma
# MAGIC    folha fotografada em outro dia conta como analise nova.

# COMMAND ----------

CATEGORIAS_VALIDAS = ["Saudável", "Doente"]
OBRIGATORIAS = ["nome_imagem", "categoria", "acuracia", "data", "localidade"]
CHAVE_DEDUPLICACAO = ["nome_imagem", "data", "localidade"]

silver = (
    spark.table(BRONZE)
    .withColumn("data", F.to_date("data", "yyyy-MM-dd"))
    .withColumn("acuracia", F.col("acuracia").cast(DoubleType()))
    .dropna(subset=OBRIGATORIAS)
    .filter(F.col("categoria").isin(CATEGORIAS_VALIDAS))
    .dropDuplicates(CHAVE_DEDUPLICACAO)
)

silver.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(SILVER)

brutos = spark.table(BRONZE).count()
tratados = spark.table(SILVER).count()
print(f"Bronze: {brutos} | Silver: {tratados} | Descartados: {brutos - tratados}")
display(spark.table(SILVER).limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Gold: indicadores do painel
# MAGIC
# MAGIC Tres tabelas, uma por pergunta que o agricultor faz:
# MAGIC
# MAGIC - `gold_resumo`: quanto da lavoura esta doente agora.
# MAGIC - `gold_por_localidade`: qual talhao concentra o problema.
# MAGIC - `gold_tendencia_diaria`: o foco esta crescendo ou cedendo.

# COMMAND ----------

silver = spark.table(SILVER)

resumo = silver.agg(
    F.count("*").alias("total_imagens"),
    F.round(
        F.sum(F.when(F.col("categoria") == "Saudável", 1).otherwise(0)) * 100.0
        / F.count("*"),
        2,
    ).alias("percentual_saudaveis"),
    F.round(
        F.sum(F.when(F.col("categoria") == "Doente", 1).otherwise(0)) * 100.0
        / F.count("*"),
        2,
    ).alias("percentual_doentes"),
    F.round(F.avg("acuracia"), 2).alias("confianca_media"),
    F.min("data").alias("primeira_coleta"),
    F.max("data").alias("ultima_coleta"),
).withColumn("gerado_em", F.current_timestamp())

resumo.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(GOLD_RESUMO)
display(spark.table(GOLD_RESUMO))

# COMMAND ----------

por_localidade = (
    silver.groupBy("localidade")
    .agg(
        F.count("*").alias("total"),
        F.sum(F.when(F.col("categoria") == "Doente", 1).otherwise(0)).alias("doentes"),
        F.sum(F.when(F.col("categoria") == "Saudável", 1).otherwise(0)).alias(
            "saudaveis"
        ),
        F.round(F.avg("acuracia"), 2).alias("confianca_media"),
    )
    .withColumn(
        "percentual_doentes", F.round(F.col("doentes") * 100.0 / F.col("total"), 2)
    )
    .orderBy(F.col("percentual_doentes").desc())
)

por_localidade.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(
    GOLD_LOCALIDADE
)
display(spark.table(GOLD_LOCALIDADE))

# COMMAND ----------

tendencia = (
    silver.groupBy("data", "localidade")
    .agg(
        F.count("*").alias("total"),
        F.sum(F.when(F.col("categoria") == "Doente", 1).otherwise(0)).alias("doentes"),
    )
    .withColumn(
        "percentual_doentes", F.round(F.col("doentes") * 100.0 / F.col("total"), 2)
    )
    .orderBy("data", "localidade")
)

tendencia.write.mode("overwrite").option("overwriteSchema", True).saveAsTable(
    GOLD_TENDENCIA
)
display(spark.table(GOLD_TENDENCIA))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Media movel de sete dias por talhao
# MAGIC
# MAGIC A contagem de um dia so oscila muito. A media movel mostra a tendencia e
# MAGIC separa um dia ruim de um foco de praga que esta crescendo de verdade.
# MAGIC
# MAGIC Uma janela deslizante por talhao e o tipo de calculo em que o Spark paga
# MAGIC pelo custo de ser distribuido.

# COMMAND ----------

from pyspark.sql.window import Window

janela = (
    Window.partitionBy("localidade")
    .orderBy(F.col("data").cast("timestamp").cast("long"))
    .rangeBetween(-6 * 86400, 0)
)

media_movel = spark.table(GOLD_TENDENCIA).withColumn(
    "media_movel_7d", F.round(F.avg("percentual_doentes").over(janela), 2)
)

display(media_movel.orderBy("localidade", "data"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Plano de execucao
# MAGIC
# MAGIC O plano mostra como o Spark resolve a consulta: leitura da tabela,
# MAGIC troca de dados entre os nos e agregacao. E o que diferencia este caminho
# MAGIC da versao em pandas, que roda tudo em uma unica maquina.

# COMMAND ----------

por_localidade.explain("formatted")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Conferencia entre os dois caminhos
# MAGIC
# MAGIC Os numeros desta celula precisam bater com `data/saida/indicadores.json`,
# MAGIC gerado pela versao em pandas com o mesmo arquivo de entrada.

# COMMAND ----------

conferencia = spark.table(GOLD_RESUMO).first()

print(f"total_imagens        {conferencia['total_imagens']}")
print(f"percentual_saudaveis {conferencia['percentual_saudaveis']}")
print(f"percentual_doentes   {conferencia['percentual_doentes']}")
print(f"confianca_media      {conferencia['confianca_media']}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Agendamento
# MAGIC
# MAGIC Para rodar sozinho, crie um Job no menu Workflows com este notebook como
# MAGIC tarefa unica e uma agenda diaria. O aplicativo grava o CSV no volume e o
# MAGIC Job atualiza as tabelas Gold todo dia, sem ninguem abrir o notebook.
