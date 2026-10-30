"""AgroVision: aplicativo Streamlit com analise, painel, decisoes e pipeline.

Rode com:
    streamlit run src/agrovision/app.py
"""

import hashlib
import io
import shutil
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

from agrovision import automacao, ingestao, pipeline, produtor
from agrovision.decisao import LIMIAR_CRITICO, REGRAS_DE_INTERVENCAO, avaliar, situacao_atual
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

# Caixa do Streamlit usada para cada regra: vermelho, amarelo ou verde.
CAIXA_POR_REGRA = {
    "R5": st.error,
    "R3": st.error,
    "R4": st.warning,
    "R2": st.warning,
    "R1": st.success,
}

st.set_page_config(page_title="AgroVision | Fase 3", page_icon="🌱", layout="wide")


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
st.caption("Classificacao e monitoramento de folhas de tomateiro | Fase 3")

aba_analise, aba_painel, aba_decisao, aba_pipeline, aba_entrada = st.tabs(
    [
        "🔬 Analise de folhas",
        "📊 Painel",
        "🧠 Inteligencia no campo",
        "🔄 Pipeline de dados",
        "📥 Entrada automatizada",
    ]
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
                        "pipeline. Alertas e relatorio de intervencao atualizados. "
                        "Veja as abas Painel e Inteligencia no campo."
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
        st.session_state.pop("relatorio", None)
        st.rerun()


with aba_decisao:
    st.write(
        "Regras de decisao da Fase 3 aplicadas por talhao e por dia, com a acao "
        "recomendada para cada situacao."
    )
    fonte = "base de demonstração" if demonstracao else "camada Silver"
    st.caption(
        f"Fonte: {fonte}. Para trocar, use o seletor de dados de demonstracao na "
        "aba Painel. Os limiares sao didaticos e as recomendacoes nao acionam "
        "nenhum equipamento."
    )

    alertas = avaliar(registros)

    if not alertas:
        st.warning(
            "Ainda nao existem analises para avaliar. Use a aba Analise de folhas ou "
            "ligue os dados de demonstracao."
        )
    else:
        atual = situacao_atual(alertas)
        intervir = sum(a["regra"] in REGRAS_DE_INTERVENCAO for a in atual)

        st.subheader("Situacao atual por talhao")
        st.caption(
            f"Ultimo dia com analises em cada talhao. {intervir} de {len(atual)} "
            "talhao(oes) pedem intervencao."
        )
        colunas = st.columns(min(len(atual), 3))
        for i, alerta in enumerate(atual):
            with colunas[i % len(colunas)]:
                CAIXA_POR_REGRA[alerta["regra"]](
                    f"**{alerta['talhao']}** | {alerta['data']}\n\n"
                    f"{alerta['nivel']} ({alerta['regra']}): "
                    f"{alerta['percentual_doentes']:.1f}% de folhas doentes\n\n"
                    f"{alerta['recomendacao']}"
                )

        decisoes = pd.DataFrame(alertas)

        st.subheader("Percentual de folhas doentes por dia")
        st.caption(
            f"Acima da linha de {LIMIAR_CRITICO}% o dia e critico (R3). Critico em "
            "3 dias seguidos com folha doente vira prioridade maxima (R5)."
        )
        evolucao = decisoes.pivot_table(
            index="data", columns="talhao", values="percentual_doentes"
        )
        evolucao[f"Limiar critico ({LIMIAR_CRITICO}%)"] = LIMIAR_CRITICO
        # Com um dia so, a linha nao tem o que ligar e o grafico sai vazio.
        if len(evolucao) > 1:
            st.line_chart(evolucao)
        else:
            st.bar_chart(evolucao.T.rename(columns=str), horizontal=True)

        st.subheader("Historico de decisoes")
        so_intervencao = st.toggle("Mostrar so os dias que pedem intervencao", value=True)
        if so_intervencao:
            decisoes = decisoes[decisoes["regra"].isin(REGRAS_DE_INTERVENCAO)]
        st.dataframe(
            decisoes[
                ["data", "talhao", "total", "doentes", "percentual_doentes", "regra",
                 "nivel", "recomendacao"]
            ].sort_values(["data", "talhao"], ascending=[False, True]),
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Relatorio de intervencao")
        st.caption(
            "O pipeline gera o relatorio sozinho a cada analise nova. O botao gera "
            "um relatorio agora com os dados exibidos."
        )
        # A demonstracao grava em uma subpasta para nao sobrescrever os alertas reais.
        destino = pipeline.SAIDA / "demonstracao" if demonstracao else pipeline.SAIDA

        if st.button("Gerar relatorio de intervencao", type="primary"):
            st.session_state["relatorio"] = automacao.executar(registros, destino, fonte)

        # O relatorio da sessao so vale para a mesma fonte de dados.
        resultado = st.session_state.get("relatorio")
        if resultado and resultado["fonte"] == fonte:
            caminho = resultado["arquivo_relatorio"]
            st.success(
                f"Relatorio gravado em {caminho.relative_to(RAIZ).as_posix()} e alertas "
                f"em {resultado['arquivo_alertas'].relative_to(RAIZ).as_posix()}."
            )
            st.download_button(
                "Baixar relatorio",
                resultado["relatorio"],
                file_name=caminho.name,
                mime="text/markdown",
            )
            with st.expander("Ver relatorio", expanded=True):
                st.markdown(resultado["relatorio"])


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


INTERVALO_MONITOR = 3
LINHAS_DE_LOG = 150


def rodar_ingestao(pasta: Path, saida: Path) -> None:
    """Processa a pasta uma vez e guarda o log da execucao na sessao."""
    registro = io.StringIO()
    with redirect_stdout(registro), pipeline.em_saida(saida):
        ingestao.processar(pasta)

    linhas = [linha for linha in registro.getvalue().splitlines() if "[Ingestao]" in linha]
    if linhas:
        log = st.session_state.setdefault(f"log_{saida}", [])
        log.extend(linhas)
        del log[:-LINHAS_DE_LOG]


def ler_estado(pasta: Path, saida: Path) -> dict:
    """Checkpoint, arquivos pendentes, tamanho da Bronze e decisoes de uma fonte.

    As decisoes saem da Silver da propria fonte, e nao do alertas.json, que o botao
    da aba Inteligencia tambem grava na pasta da demonstracao.
    """
    with pipeline.em_saida(saida):
        checkpoint = ingestao.ler_checkpoint()
        pendentes = {arquivo.name for arquivo in ingestao.pendentes(pasta, checkpoint)}
        bronze = len(pipeline.ler_camada(pipeline.BRONZE))
        alertas = avaliar(pipeline.ler_camada(pipeline.SILVER).to_dict("records"))

    return {
        "checkpoint": checkpoint["arquivos"],
        "pendentes": pendentes,
        "arquivos": [arquivo.name for arquivo in ingestao.listar_arquivos(pasta)],
        "bronze": bronze,
        "alertas": alertas,
    }


@st.fragment(run_every=INTERVALO_MONITOR)
def exibir_entrada(pasta: Path, saida: Path, demonstracao: bool) -> None:
    """Estado da entrada automatizada. Atualiza sozinho a cada INTERVALO_MONITOR s."""
    if st.session_state.get("monitorar"):
        rodar_ingestao(pasta, saida)

    st.markdown("**Acoes**")
    botoes = st.columns(4 if demonstracao else 1)
    if botoes[0].button("Processar a pasta agora", type="primary", use_container_width=True):
        rodar_ingestao(pasta, saida)

    if demonstracao:
        try:
            if botoes[1].button("Entregar proximo lote", use_container_width=True):
                produtor.entregar(pasta, aviso=lambda _: None)
            if botoes[2].button("Reenviar ultimo lote", use_container_width=True):
                produtor.reenviar(pasta)
        except ValueError as erro:
            st.warning(str(erro))

        if botoes[3].button("Reiniciar a demonstracao", use_container_width=True):
            produtor.reiniciar(pasta)
            shutil.rmtree(saida, ignore_errors=True)
            st.session_state.pop(f"log_{saida}", None)

    estado = ler_estado(pasta, saida)
    checkpoint = estado["checkpoint"]
    rejeitados = sum(item["status"] == ingestao.REJEITADO for item in checkpoint.values())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Arquivos na pasta", len(estado["arquivos"]))
    m2.metric("Aguardando leitura", len(estado["pendentes"]))
    m3.metric("Rejeitados", rejeitados)
    m4.metric("Registros na Bronze", estado["bronze"])

    st.subheader("Arquivos e checkpoint")
    if estado["arquivos"]:
        tabela = pd.DataFrame(
            [
                {
                    "arquivo": nome,
                    "situacao": "pendente"
                    if nome in estado["pendentes"]
                    else checkpoint[nome]["status"],
                    "linhas": checkpoint.get(nome, {}).get("linhas"),
                    "registros novos": checkpoint.get(nome, {}).get("novos"),
                    "lido em": checkpoint.get(nome, {}).get("processado_em"),
                    "motivo": checkpoint.get(nome, {}).get("motivo"),
                }
                for nome in estado["arquivos"]
            ]
        )
        st.dataframe(tabela, use_container_width=True, hide_index=True)
    else:
        st.info("A pasta de entrada esta vazia. Aguardando dados.")

    st.subheader("Situacao atual por talhao")
    if estado["alertas"]:
        atual = situacao_atual(estado["alertas"])
        cartoes = st.columns(min(len(atual), 3))
        for i, alerta in enumerate(atual):
            with cartoes[i % len(cartoes)]:
                CAIXA_POR_REGRA[alerta["regra"]](
                    f"**{alerta['talhao']}** | {alerta['data']}\n\n"
                    f"{alerta['nivel']} ({alerta['regra']}): "
                    f"{alerta['percentual_doentes']:.1f}% de folhas doentes\n\n"
                    f"{alerta['recomendacao']}"
                )
    else:
        st.info("Ainda nao ha alertas. Eles aparecem quando chega o primeiro lote.")

    st.subheader("Log da ingestao")
    log = st.session_state.get(f"log_{saida}", [])
    st.code("\n".join(log[-40:]) or "Sem eventos nesta sessao.", language="text")


with aba_entrada:
    st.write(
        "O sistema vigia a pasta de entrada, le so os registros ainda nao vistos e "
        "dispara o pipeline e as regras de decisao."
    )
    st.caption(
        "Modelo micro-batch com checkpoint do que ja foi lido. Um arquivo reenviado nao "
        "gera alerta nem relatorio de novo. A demonstracao grava em "
        "data/saida/demonstracao e nunca mistura registros simulados com os reais."
    )

    escolha, chave = st.columns([2, 1])
    fonte_entrada = escolha.radio(
        "Fonte", ["Demonstracao", "Dados reais"], horizontal=True, key="fonte_entrada"
    )
    chave.toggle("Monitorar a pasta automaticamente (a cada 3 s)", key="monitorar")
    entrada_demo = fonte_entrada == "Demonstracao"
    pasta_entrada = ingestao.ENTRADA_DEMO if entrada_demo else ingestao.ENTRADA
    saida_entrada = pipeline.SAIDA / automacao.DEMONSTRACAO if entrada_demo else pipeline.SAIDA

    st.caption(f"Pasta vigiada: {pasta_entrada.relative_to(RAIZ).as_posix()}")

    pasta_entrada.mkdir(parents=True, exist_ok=True)
    exibir_entrada(pasta_entrada, saida_entrada, entrada_demo)
