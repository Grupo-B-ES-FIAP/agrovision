"""AgroVision: aplicativo Streamlit com analise, painel e pipeline.

Rode com:
    streamlit run src/agrovision/app.py
"""

import hashlib
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from agrovision import pipeline
from agrovision.esquema import (
    ACURACIA,
    CATEGORIA,
    CATEGORIAS_VALIDAS,
    CODIFICACAO,
    CORES,
    DATA,
    DOENTE,
    FORMATO_DATA,
    LOCALIDADE,
    LOCALIDADES_PADRAO,
    NOME_IMAGEM,
    ORIGEM,
    ORIGEM_MODELO,
    SEPARADOR,
)
from agrovision.exportacao import gerar_csv, gerar_json
from agrovision.modelo import carregar as carregar_modelo
from agrovision.modelo import prever
from agrovision.vision import de_bytes

RAIZ = Path(__file__).resolve().parents[2]
DEMO = RAIZ / "data" / "exemplos" / "analises_demo.csv"

# Ordem igual a de CATEGORIAS_VALIDAS, que e a ordem das colunas nos graficos.
PALETA = [CORES[categoria] for categoria in CATEGORIAS_VALIDAS]

st.set_page_config(page_title="AgroVision | Fase 2", page_icon="🌱", layout="wide")


@st.cache_resource
def modelo_em_cache():
    return carregar_modelo()


@st.cache_data
def dados_demonstracao() -> list[dict]:
    """Base de demonstracao versionada no repositorio.

    Sao registros de exemplo, nao inferencias do modelo. Servem para o painel
    ter graficos quando ninguem analisou imagem nenhuma ainda.
    """
    if not DEMO.exists():
        return []

    return pd.read_csv(DEMO, sep=SEPARADOR, encoding=CODIFICACAO).to_dict("records")


def dados_reais() -> list[dict]:
    """Camada Silver do pipeline: a fonte do painel para dados reais."""
    pipeline.garantir()
    return pipeline.ler_camada(pipeline.SILVER).to_dict("records")


def preparar(registros: list[dict]) -> pd.DataFrame:
    """Converte os registros em DataFrame e descarta linhas sem data ou valor."""
    df = pd.DataFrame(registros)

    if df.empty:
        return df

    df[DATA] = pd.to_datetime(df[DATA], errors="coerce")
    df[ACURACIA] = pd.to_numeric(df[ACURACIA], errors="coerce")

    return df.dropna(subset=[DATA, ACURACIA])


st.title("🌱 AgroVision")
st.caption("Classificacao e monitoramento de folhas de tomateiro | Fase 2")

aba_analise, aba_painel, aba_pipeline = st.tabs(
    ["🔬 Analise de folhas", "📊 Painel", "🔄 Pipeline de dados"]
)


with aba_analise:
    st.write("Envie imagens de folhas de tomateiro para classificar saudavel ou doente.")

    localidade = st.selectbox("Local da coleta", [*LOCALIDADES_PADRAO, "Outro"])

    if localidade == "Outro":
        localidade = st.text_input("Nome do local", max_chars=60).strip()

    dia_coleta = st.date_input("Data da coleta", value=date.today(), max_value=date.today())

    arquivos = st.file_uploader(
        "Selecione uma ou mais imagens",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="imagens",
    )

    if st.button("Analisar e salvar imagens", type="primary"):
        if not arquivos or not localidade:
            st.warning("Selecione imagens e informe o local da coleta.")
        else:
            try:
                modelo = modelo_em_cache()
                processadas = st.session_state.setdefault("processadas", set())
                novos = []

                for arquivo in arquivos:
                    conteudo = arquivo.getvalue()
                    caracteristicas = de_bytes(conteudo)

                    if caracteristicas is None:
                        st.warning(f"Nao foi possivel ler {arquivo.name}.")
                        continue

                    # A mesma imagem pode ser analisada em outra data ou talhao.
                    # O hash do conteudo evita contar duas vezes o mesmo envio.
                    chave = (
                        hashlib.sha256(conteudo).hexdigest(),
                        dia_coleta.isoformat(),
                        localidade,
                    )

                    if chave in processadas:
                        st.info(
                            f"{arquivo.name} foi processada nesta sessao "
                            "para este local e esta data."
                        )
                        continue

                    categoria, confianca = prever(modelo, caracteristicas)
                    novos.append(
                        {
                            NOME_IMAGEM: arquivo.name,
                            CATEGORIA: categoria,
                            ACURACIA: confianca,
                            DATA: dia_coleta.isoformat(),
                            LOCALIDADE: localidade,
                            ORIGEM: ORIGEM_MODELO,
                        }
                    )
                    processadas.add(chave)

                    with st.expander(f"{arquivo.name}: {categoria} ({confianca:.2f}%)"):
                        st.image(conteudo, width=360)

                if novos:
                    pipeline.acrescentar_bronze(novos)
                    pipeline.executar()
                    st.success(
                        f"{len(novos)} analise(s) gravada(s) e processada(s) pelo "
                        "pipeline. Veja a aba Painel."
                    )

            except Exception as erro:
                st.error(f"Falha na analise: {erro}")

    st.caption(
        "A confianca e a probabilidade estimada pelo modelo para aquela imagem, "
        "nao uma medida de acuracia geral."
    )


with aba_painel:
    demonstracao = st.toggle(
        "Exibir dados de demonstracao",
        value=not pipeline.SILVER.exists(),
        help="Use os dados de demonstracao para ver o painel antes de analisar imagens.",
    )

    registros = dados_demonstracao() if demonstracao else dados_reais()

    if demonstracao:
        st.info(
            "Dados de demonstracao: registros de exemplo para mostrar os graficos. "
            "Nenhuma doenca especifica foi identificada pelo modelo."
        )
    else:
        st.info(
            "Dados reais: classificacoes feitas neste aplicativo, tratadas pelo "
            "pipeline ETL (camada Silver)."
        )

    df = preparar(registros)

    if df.empty:
        st.warning(
            "Ainda nao existem analises. Use a aba Analise de folhas ou ligue os "
            "dados de demonstracao."
        )
    else:
        menor, maior = df[DATA].dt.date.min(), df[DATA].dt.date.max()
        locais = sorted(df[LOCALIDADE].unique())

        f1, f2, f3 = st.columns(3)
        intervalo = f1.date_input(
            "Periodo", value=(menor, maior), min_value=menor, max_value=maior
        )
        escolhidos = f2.multiselect("Localidade", locais, default=locais)
        categorias = f3.multiselect(
            "Classificacao", CATEGORIAS_VALIDAS, default=CATEGORIAS_VALIDAS
        )

        if isinstance(intervalo, tuple) and len(intervalo) == 2:
            df = df[df[DATA].dt.date.between(*intervalo)]

        df = df[df[LOCALIDADE].isin(escolhidos) & df[CATEGORIA].isin(categorias)]

        if df.empty:
            st.warning("Nenhum registro corresponde aos filtros escolhidos.")
        else:
            total = len(df)
            doentes = int((df[CATEGORIA] == DOENTE).sum())
            saudaveis = total - doentes

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Imagens analisadas", total)
            m2.metric("Saudaveis", f"{saudaveis / total:.1%}")
            m3.metric("Doentes", f"{doentes / total:.1%}")
            m4.metric("Confianca media", f"{df[ACURACIA].mean():.1f}%")

            esquerda, direita = st.columns(2)

            with esquerda:
                st.subheader("Distribuicao das classificacoes")
                # Uma linha com as duas categorias em colunas, para cada barra
                # receber a sua cor. O indice vira o rotulo do eixo.
                contagem = (
                    df[CATEGORIA]
                    .value_counts()
                    .reindex(CATEGORIAS_VALIDAS, fill_value=0)
                    .to_frame()
                    .T.rename(index={"count": "Imagens analisadas"})
                )
                st.bar_chart(contagem, color=PALETA, stack=False)

            with direita:
                st.subheader("Analises por localidade")
                por_local = pd.crosstab(df[LOCALIDADE], df[CATEGORIA]).reindex(
                    columns=CATEGORIAS_VALIDAS, fill_value=0
                )
                st.bar_chart(por_local, color=PALETA)

            st.subheader("Evolucao por dia")
            st.caption(
                "Uma linha de doentes subindo em um talhao indica foco de praga "
                "e sugere acao preventiva naquele talhao."
            )
            diario = (
                df.groupby([df[DATA].dt.date, CATEGORIA])
                .size()
                .unstack(fill_value=0)
                .reindex(columns=CATEGORIAS_VALIDAS, fill_value=0)
            )
            st.line_chart(diario, color=PALETA)

            st.subheader("Historico filtrado")
            exibicao = df.copy()
            exibicao[DATA] = exibicao[DATA].dt.strftime(FORMATO_DATA)
            st.dataframe(exibicao, use_container_width=True, hide_index=True)

            registros_exibidos = exibicao.to_dict("records")
            c1, c2 = st.columns(2)
            c1.download_button(
                "Baixar CSV filtrado",
                gerar_csv(registros_exibidos),
                file_name="analises_filtradas.csv",
                mime="text/csv",
            )
            c2.download_button(
                "Baixar JSON filtrado",
                gerar_json(registros_exibidos),
                file_name="analises_filtradas.json",
                mime="application/json",
            )

    pode_limpar = not demonstracao and pipeline.BRONZE.exists()

    if pode_limpar and st.button("Apagar historico salvo", type="secondary"):
        pipeline.limpar()
        st.session_state.pop("processadas", None)
        st.rerun()


with aba_pipeline:
    st.write("Pipeline ETL da integracao com a base de dados: Bronze, Silver e Gold.")
    st.caption(
        "A Bronze recebe o resultado de cada classificacao. A Silver valida e "
        "deduplica, e alimenta o painel. A Gold guarda os indicadores agregados."
    )

    if st.button("Reprocessar pipeline", type="primary"):
        pipeline.executar()
        st.success("Pipeline executado: camadas Silver e Gold atualizadas.")
    else:
        pipeline.garantir()

    bronze = pipeline.ler_camada(pipeline.BRONZE)
    silver = pipeline.ler_camada(pipeline.SILVER)

    if bronze.empty:
        st.info(
            "Ainda nao existem dados. Analise imagens na aba Analise de folhas e o "
            "pipeline roda automaticamente."
        )
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros brutos (Bronze)", len(bronze))
        c2.metric("Registros tratados (Silver)", len(silver))
        c3.metric("Descartados na validacao", len(bronze) - len(silver))

        st.subheader("1. Ingestao: dados brutos (Bronze)")
        st.dataframe(bronze, use_container_width=True, hide_index=True)

        st.subheader("2. Transformacao: dados tratados (Silver)")
        st.dataframe(silver, use_container_width=True, hide_index=True)

        st.subheader("3. Carga: indicadores agregados (Gold)")
        if pipeline.GOLD.exists():
            st.json(pipeline.GOLD.read_text(encoding="utf-8"))

        st.caption(
            f"Arquivos em data/saida/: {pipeline.BRONZE.name}, "
            f"{pipeline.SILVER.name}, {pipeline.GOLD.name}"
        )
