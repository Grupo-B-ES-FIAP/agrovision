"""Extracao de caracteristicas visuais de uma folha.

Este modulo e a unica fonte da verdade do vetor de caracteristicas.
O treino e a inferencia usam as mesmas constantes e a mesma rotina, de modo
que um ajuste aqui nunca deixa o modelo e o aplicativo fora de sincronia.

Metodo: a imagem e reduzida para um tamanho fixo, convertida para o espaco de
cor HSV e descrita por tres histogramas normalizados, um por canal. Matiz,
saturacao e brilho separam bem folha verde de folha com mancha necrosada.
"""

from pathlib import Path

import cv2
import numpy as np

TAMANHO = (128, 128)
BINS = 32
CANAIS = ((0, 180), (1, 256), (2, 256))
N_CARACTERISTICAS = BINS * len(CANAIS)


def de_imagem(imagem: np.ndarray) -> np.ndarray:
    """Descreve uma imagem BGR ja carregada como um vetor de 96 numeros."""
    hsv = cv2.cvtColor(cv2.resize(imagem, TAMANHO), cv2.COLOR_BGR2HSV)
    histogramas = []

    for canal, limite in CANAIS:
        histograma = cv2.calcHist([hsv], [canal], None, [BINS], [0, limite])
        histogramas.append(cv2.normalize(histograma, histograma).flatten())

    return np.concatenate(histogramas)


def de_bytes(conteudo: bytes) -> np.ndarray | None:
    """Descreve uma imagem recebida como bytes, por exemplo de um upload.

    Devolve None quando os bytes nao formam uma imagem que o OpenCV leia.
    """
    imagem = cv2.imdecode(np.frombuffer(conteudo, np.uint8), cv2.IMREAD_COLOR)

    if imagem is None:
        return None

    return de_imagem(imagem)


def de_arquivo(caminho: str | Path) -> np.ndarray | None:
    """Descreve uma imagem lida do disco.

    Devolve None quando o arquivo nao existe ou nao e uma imagem valida.
    """
    imagem = cv2.imread(str(caminho))

    if imagem is None:
        return None

    return de_imagem(imagem)
