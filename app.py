import streamlit as st
import cv2
import numpy as np
import joblib
import tempfile

# Exportar dados 
from exportar_dados import gerar_csv, gerar_json

# Carregar o modelo treinado
modelo = joblib.load("modelo_folhas.pkl")


def extrair_caracteristicas(caminho_imagem):
    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        return None

    imagem = cv2.resize(imagem, (128, 128))

    hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)

    hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
    hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
    hist_v = cv2.calcHist([hsv], [2], None, [32], [0, 256])

    hist_h = cv2.normalize(hist_h, hist_h).flatten()
    hist_s = cv2.normalize(hist_s, hist_s).flatten()
    hist_v = cv2.normalize(hist_v, hist_v).flatten()

    caracteristicas = np.concatenate([
        hist_h,
        hist_s,
        hist_v
    ])

    return caracteristicas


# Configuração da página
st.set_page_config(
    page_title="AgroVision",
    page_icon="🌱",
    layout="centered"
)


st.title("🌱 AgroVision")

st.subheader("Classificação de folhas de tomateiro")

st.write(
    "Envie uma imagem de uma folha de tomateiro para verificar "
    "se ela está saudável ou apresenta sinais de doença."
)

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
        
arquivos = st.file_uploader(
    "Selecione uma ou mais imagens",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
    key=f"uploader_{st.session_state.uploader_key}"
)


if arquivos:
    #deixar a rolagem separada
    area_resultados = st.container(height=500, border=True)
    for arquivo in arquivos:
        
         with area_resultados:
             
            # Mostrar imagem
            st.image(
                arquivo,
                caption="Imagem selecionada",
                width=400
            )

            # Criar arquivo temporário para o OpenCV
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".jpg"
            ) as temp:

                temp.write(arquivo.getbuffer())
                caminho_imagem = temp.name


            caracteristicas = extrair_caracteristicas(caminho_imagem)


            if caracteristicas is not None:

                entrada = caracteristicas.reshape(1, -1)

                previsao = modelo.predict(entrada)[0]

                probabilidades = modelo.predict_proba(entrada)[0]

                confianca = max(probabilidades) * 100


                st.divider()

                st.subheader("Resultado da análise")


                if previsao == 0:

                    st.success("✅ Folha classificada como SAUDÁVEL")

                else:

                    st.error("⚠️ Folha classificada como DOENTE")


                st.metric(
                    "Confiança do modelo",
                    f"{confianca:.2f}%"
                )


                st.caption(
                    "Protótipo acadêmico desenvolvido para classificação "
                    "de folhas de tomateiro utilizando visão computacional."
                )
                
                categoria = "Saudável" if previsao == 0 else "Doente"

                if "resultados" not in st.session_state:
                    st.session_state.resultados = []
                    
                nomes_ja_registrados = [
                    r["nome_imagem"] for r in st.session_state.resultados
                ]
                if arquivo.name not in nomes_ja_registrados:
                    st.session_state.resultados.append({
                        "nome_imagem": arquivo.name,
                        "categoria": categoria,
                        "acuracia": confianca ,
                    })

if "resultados" in st.session_state and st.session_state.resultados:
    st.divider()
    st.subheader("📩 Exportar resultados")
    st.markdown("""
        <style>
        div[data-testid="stDownloadButton"] button {
            background-color: #2ecc71;
            color: white;
            border: none;
        }
        div[data-testid="stDownloadButton"] button:hover {
            background-color: #27ae60;
            color: white;
        }
        div[data-testid="stButton"] button {
            background-color: #e74c3c;
            color: white;
            border: none;
        }
        div[data-testid="stButton"] button:hover {
            background-color: #c0392b;
            color: white;
        }
        </style>
    """, unsafe_allow_html=True)
    
    exportar_csv = gerar_csv(st.session_state.resultados)
    exportar_json = gerar_json(st.session_state.resultados)
    
    col_exportar, col_apagar = st.columns([2, 1])
   
    with col_exportar:
        col_csv, col_json = st.columns(2)
        
        with col_csv:
                st.download_button(
                    label="Baixar CSV",
                    data=exportar_csv,
                    file_name="resultados_agrovision.csv",
                    mime="text/csv",
                )
        with col_json:
                    st.download_button(
                        label="Baixar JSON",
                        data=exportar_json,
                        file_name="resultados_agrovision.json",
                        mime="application/json",
                    )
                    
    with col_apagar:
        if st.button("Apagar histórico de dados"):
                st.session_state.resultados = []
                st.session_state.uploader_key += 1
                st.rerun()
    
    st.write(
        "Exporte os resultados de todas as imagens que realizou a classificação"
        "Formatos disponíveis: CSV ou JSON"
    )
    resultados_exibicao = [
        {
            "nome_imagem": r["nome_imagem"],
            "categoria": r["categoria"],
            "acuracia": f"{r['acuracia']}%",
        }
        for r in st.session_state.resultados
    
    ]
    st.dataframe(
        resultados_exibicao,
        width="stretch"
    )
    

        