import os
import cv2
import numpy as np
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report


# Caminhos das imagens
PASTA_SAUDAVEL = "dataset/saudavel"
PASTA_DOENTE = "dataset/doente"


def extrair_caracteristicas(caminho_imagem):
    """
    Lê uma imagem e transforma suas características visuais
    em números que o modelo consegue utilizar.
    """

    imagem = cv2.imread(caminho_imagem)

    if imagem is None:
        return None

    # Padroniza o tamanho
    imagem = cv2.resize(imagem, (128, 128))

    # Converte BGR para HSV
    hsv = cv2.cvtColor(imagem, cv2.COLOR_BGR2HSV)

    # Calcula histogramas de cor
    hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180])
    hist_s = cv2.calcHist([hsv], [1], None, [32], [0, 256])
    hist_v = cv2.calcHist([hsv], [2], None, [32], [0, 256])

    # Normaliza os histogramas
    hist_h = cv2.normalize(hist_h, hist_h).flatten()
    hist_s = cv2.normalize(hist_s, hist_s).flatten()
    hist_v = cv2.normalize(hist_v, hist_v).flatten()

    # Junta tudo em um único vetor
    caracteristicas = np.concatenate([hist_h, hist_s, hist_v])

    return caracteristicas


def carregar_imagens(pasta, classe):
    dados = []
    classes = []

    for arquivo in os.listdir(pasta):

        caminho = os.path.join(pasta, arquivo)

        caracteristicas = extrair_caracteristicas(caminho)

        if caracteristicas is not None:
            dados.append(caracteristicas)
            classes.append(classe)

    return dados, classes


print("Carregando imagens...")


# Folhas saudáveis = 0
dados_saudaveis, classes_saudaveis = carregar_imagens(
    PASTA_SAUDAVEL,
    0
)

# Folhas doentes = 1
dados_doentes, classes_doentes = carregar_imagens(
    PASTA_DOENTE,
    1
)


X = np.array(dados_saudaveis + dados_doentes)
y = np.array(classes_saudaveis + classes_doentes)


print(f"Total de imagens carregadas: {len(X)}")
print(f"Saudáveis: {len(dados_saudaveis)}")
print(f"Doentes: {len(dados_doentes)}")


# Separação treino/teste
X_treino, X_teste, y_treino, y_teste = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)


print("\nTreinando modelo...")


modelo = RandomForestClassifier(
    n_estimators=200,
    random_state=42
)

modelo.fit(X_treino, y_treino)


# Teste do modelo
previsoes = modelo.predict(X_teste)

acuracia = accuracy_score(y_teste, previsoes)


print("\n-----------------------------")
print("RESULTADO DO TREINAMENTO")
print("-----------------------------")

print(f"Acurácia: {acuracia * 100:.2f}%")

print("\nRelatório:")
print(
    classification_report(
        y_teste,
        previsoes,
        target_names=["Saudável", "Doente"]
    )
)


# Salvar modelo
joblib.dump(modelo, "modelo_folhas.pkl")

print("\nModelo salvo como: modelo_folhas.pkl")