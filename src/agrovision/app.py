from datetime import date, datetime, timedelta
from pathlib import Path
import csv
import hashlib
import io

import cv2
import joblib
import numpy as np
import pandas as pd
import streamlit as st

from agrovision.exportacao import CAMPOS, gerar_csv, gerar_json
from agrovision.pipeline import (
    ARQUIVO_BRUTO,
    ARQUIVO_INDICADORES,
    ARQUIVO_TRATADO,
    executar_pipeline,
    garantir_pipeline,
)

RAIZ = Path(__file__).resolve().parents[2]
MODELO = RAIZ / "models" / "modelo_folhas.pkl"
HISTORICO = RAIZ / "data" / "saida" / "analises.csv"

st.set_page_config(
    page_title="AgroVision | Fase 2",
    page_icon="🌱",
    layout="wide",
)


@st.cache_resource
def carregar_modelo():
    return joblib.load(MODELO)


def extrair_caracteristicas(conteudo):
    imagem = cv2.imdecode(
        np.frombuffer(conteudo, np.uint8),
        cv2.IMREAD_COLOR,
    )
    if imagem is None:
        return None

    hsv = cv2.cvtColor(
        cv2.resize(imagem, (128, 128)),
        cv2.COLOR_BGR2HSV,
    )
    histogramas = []

    for canal, limites in [(0, 180), (1, 256), (2, 256)]:
        hist = cv2.calcHist(
            [hsv],
            [canal],
            None,
            [32],
            [0, limites],
        )
        histogramas.append(cv2.normalize(hist, hist).flatten())

    return np.concatenate(histogramas)


def carregar_historico():
    if not HISTORICO.exists():
        return []

    with HISTORICO.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def carregar_dados_tratados():
    # Camada Silver do pipeline ETL: é a fonte do Dashboard para dados reais
    garantir_pipeline()

    if not ARQUIVO_TRATADO.exists():
        return []

    with ARQUIVO_TRATADO.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def ler_camada(caminho):
    # Lê uma camada do pipeline (Bronze/Silver) como DataFrame, sem reprocessar
    if not caminho.exists():
        return pd.DataFrame(columns=CAMPOS)

    return pd.read_csv(caminho, sep=";", encoding="utf-8-sig")


def salvar_historico(resultados):
    HISTORICO.parent.mkdir(parents=True, exist_ok=True)

    with HISTORICO.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(
            arquivo,
            fieldnames=CAMPOS,
            delimiter=";",
        )
        escritor.writeheader()
        escritor.writerows(resultados)


def dados_simulados():
    # Somente demonstração: estes registros não são inferências do modelo.
    inicio = date.today() - timedelta(days=29)
    registros = []

    for indice in range(90):
        dia = inicio + timedelta(days=indice % 30)
        doente = (indice * 17 + indice // 30) % 10 < 4

        registros.append(
            {
                "nome_imagem": f"exemplo_{indice + 1:03}.jpg",
                "categoria": "Doente" if doente else "Saudável",
                "acuracia": round(78 + (indice * 7) % 20 + 0.35, 2),
                "data": dia.isoformat(),
                "localidade": ["Talhão A", "Talhão B", "Talhão C"][indice % 3],
                "origem": "Simulado",
            }
        )

    return registros


st.title("🌱 AgroVision")
st.caption("Classificação e monitoramento de folhas de tomateiro | Fase 2")
aba_analise, aba_dashboard, aba_pipeline = st.tabs(
    ["🔬 Análise de folhas", "📊 Dashboard", "🔄 Pipeline de dados"]
)


with aba_analise:
    st.write(
        "Envie imagens de folhas de tomateiro para classificação saudável/doente."
    )
    localidade = st.selectbox(
        "Local da coleta",
        ["Talhão A", "Talhão B", "Talhão C", "Outro"],
    )

    if localidade == "Outro":
        localidade = st.text_input(
            "Nome do local",
            max_chars=60,
        ).strip()

    dia_coleta = st.date_input(
        "Data da coleta",
        value=date.today(),
        max_value=date.today(),
    )

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
                modelo = carregar_modelo()
                historico = carregar_historico()
                novos = 0

                for arquivo in arquivos:
                    conteudo = arquivo.getvalue()
                    caracteristicas = extrair_caracteristicas(conteudo)

                    if caracteristicas is None:
                        st.warning(f"Não foi possível ler {arquivo.name}.")
                        continue

                    entrada = caracteristicas.reshape(1, -1)
                    previsao = modelo.predict(entrada)[0]
                    categoria = "Saudável" if previsao == 0 else "Doente"
                    confianca = round(
                        float(max(modelo.predict_proba(entrada)[0]) * 100),
                        2,
                    )

                    # A mesma imagem pode ser analisada em outra data ou talhão.
                    digest = hashlib.sha256(conteudo).hexdigest()
                    chave = (
                        digest,
                        dia_coleta.isoformat(),
                        localidade,
                    )

                    if chave in st.session_state.get(
                        "imagens_processadas",
                        set(),
                    ):
                        st.info(
                            f"{arquivo.name} já foi processada nesta sessão "
                            "para este local e data."
                        )
                        continue

                    historico.append(
                        {
                            "nome_imagem": arquivo.name,
                            "categoria": categoria,
                            "acuracia": confianca,
                            "data": dia_coleta.isoformat(),
                            "localidade": localidade,
                            "origem": "Modelo",
                        }
                    )

                    st.session_state.setdefault(
                        "imagens_processadas",
                        set(),
                    ).add(chave)

                    novos += 1

                    with st.expander(
                        f"{arquivo.name}: {categoria} ({confianca:.2f}%)"
                    ):
                        st.image(conteudo, width=360)

                if novos:
                    salvar_historico(historico)
                    executar_pipeline()
                    st.success(
                        f"{novos} análise(s) salva(s) e processada(s) pelo pipeline. "
                        "Veja a aba Dashboard."
                    )

            except Exception as erro:
                st.error(f"Falha na análise: {erro}")

    st.caption(
        "A confiança é a probabilidade estimada pelo modelo, "
        "não uma medição de acurácia geral."
    )


with aba_dashboard:
    demonstracao = st.toggle(
        "Exibir dados simulados para demonstração",
        value=not HISTORICO.exists(),
    )
    registros = (
        dados_simulados()
        if demonstracao
        else carregar_dados_tratados()
    )

    if demonstracao:
        st.info(
            "Dados simulados: exemplos para demonstrar os gráficos. "
            "Nenhuma doença específica foi identificada pelo modelo."
        )
    else:
        st.info(
            "Dados reais: classificações feitas neste aplicativo, "
            "tratadas pelo pipeline ETL (dados/analises_tratadas.csv)."
        )

    if not registros:
        st.warning(
            "Ainda não há análises salvas. "
            "Use a aba Análise de folhas ou ative os dados simulados."
        )
    else:
        df = pd.DataFrame(registros)
        df["data"] = pd.to_datetime(df["data"], errors="coerce")
        df["acuracia"] = pd.to_numeric(
            df["acuracia"],
            errors="coerce",
        )
        df = df.dropna(subset=["data", "acuracia"])

        if df.empty:
            st.warning("Os registros não têm datas e confianças válidas.")
        else:
            menor = df["data"].dt.date.min()
            maior = df["data"].dt.date.max()

            intervalo = st.date_input(
                "Período",
                value=(menor, maior),
                min_value=menor,
                max_value=maior,
            )

            locais = st.multiselect(
                "Localidade",
                sorted(df["localidade"].unique()),
                default=sorted(df["localidade"].unique()),
            )

            categorias = st.multiselect(
                "Classificação",
                ["Saudável", "Doente"],
                default=["Saudável", "Doente"],
            )

            if isinstance(intervalo, tuple) and len(intervalo) == 2:
                df = df[
                    df["data"].dt.date.between(
                        intervalo[0],
                        intervalo[1],
                    )
                ]

            df = df[
                df["localidade"].isin(locais)
                & df["categoria"].isin(categorias)
            ]

            if df.empty:
                st.warning(
                    "Nenhum registro corresponde aos filtros escolhidos."
                )
            else:
                total = len(df)
                saudaveis = int(
                    (df["categoria"] == "Saudável").sum()
                )
                doentes = int(
                    (df["categoria"] == "Doente").sum()
                )

                colunas = st.columns(4)

                for coluna, titulo, valor in zip(
                    colunas,
                    [
                        "Imagens analisadas",
                        "Saudáveis",
                        "Doentes",
                        "Confiança média",
                    ],
                    [
                        total,
                        f"{saudaveis / total:.1%}",
                        f"{doentes / total:.1%}",
                        f"{df['acuracia'].mean():.1f}%",
                    ],
                ):
                    coluna.metric(titulo, valor)

                esquerda, direita = st.columns(2)

                with esquerda:
                    st.subheader("Distribuição das classificações")
                    st.bar_chart(
                        df["categoria"]
                        .value_counts()
                        .reindex(
                            ["Saudável", "Doente"],
                            fill_value=0,
                        )
                    )

                with direita:
                    st.subheader("Análises por localidade")
                    st.bar_chart(
                        pd.crosstab(
                            df["localidade"],
                            df["categoria"],
                        )
                    )

                st.subheader("Evolução por dia")
                diario = (
                    df.groupby(
                        [df["data"].dt.date, "categoria"]
                    )
                    .size()
                    .unstack(fill_value=0)
                )

                st.line_chart(
                    diario.reindex(
                        columns=["Saudável", "Doente"],
                        fill_value=0,
                    )
                )

                st.subheader("Histórico filtrado")
                exibicao = df.copy()
                exibicao["data"] = exibicao["data"].dt.strftime(
                    "%Y-%m-%d"
                )

                st.dataframe(
                    exibicao,
                    use_container_width=True,
                    hide_index=True,
                )

                c1, c2 = st.columns(2)

                c1.download_button(
                    "Baixar CSV filtrado",
                    gerar_csv(exibicao.to_dict("records")),
                    file_name="analises_filtradas.csv",
                    mime="text/csv",
                )

                c2.download_button(
                    "Baixar JSON filtrado",
                    gerar_json(exibicao.to_dict("records")),
                    file_name="analises_filtradas.json",
                    mime="application/json",
                )

    if not demonstracao and HISTORICO.exists():
        if st.button("Apagar histórico salvo", type="secondary"):
            for camada in (
                HISTORICO,
                ARQUIVO_TRATADO,
                ARQUIVO_INDICADORES,
            ):
                camada.unlink(missing_ok=True)

            st.session_state.pop("imagens_processadas", None)
            st.rerun()


with aba_pipeline:
    st.write(
        "Pipeline ETL da integração com a base de dados: "
        "**Ingestão → Transformação → Carga**."
    )
    st.caption(
        "Fonte: dados/analises.csv (gerado pela aba Análise de folhas). "
        "O Dashboard lê a camada tratada (Silver)."
    )

    if st.button("▶️ Reprocessar pipeline", type="primary"):
        executar_pipeline()
        st.success("Pipeline executado: camadas Silver e Gold atualizadas.")
    else:
        garantir_pipeline()

    bruto = ler_camada(ARQUIVO_BRUTO)
    tratado = ler_camada(ARQUIVO_TRATADO)

    if bruto.empty:
        st.info(
            "Ainda não há dados. Analise imagens na aba Análise de folhas "
            "e o pipeline será executado automaticamente."
        )
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros brutos (Bronze)", len(bruto))
        c2.metric("Registros tratados (Silver)", len(tratado))
        c3.metric("Descartados na validação", len(bruto) - len(tratado))

        st.subheader("1️⃣ Ingestão — dados brutos (Bronze)")
        st.dataframe(bruto, use_container_width=True, hide_index=True)

        st.subheader("2️⃣ Transformação — dados tratados (Silver)")
        st.dataframe(tratado, use_container_width=True, hide_index=True)

        st.subheader("3️⃣ Carga — indicadores agregados (Gold)")
        if ARQUIVO_INDICADORES.exists():
            st.json(ARQUIVO_INDICADORES.read_text(encoding="utf-8"))

        st.caption(
            f"Arquivos em dados/: {ARQUIVO_BRUTO.name}, "
            f"{ARQUIVO_TRATADO.name}, {ARQUIVO_INDICADORES.name}"
        )