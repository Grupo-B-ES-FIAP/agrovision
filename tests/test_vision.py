"""Testes da extracao de caracteristicas.

O vetor de caracteristicas e o contrato entre o treino e a inferencia. Se ele
mudar de tamanho ou deixar de ser estavel, o modelo salvo para de servir.
"""

import cv2
import numpy as np
from conftest import imagem_solida

from agrovision.vision import N_CARACTERISTICAS, de_arquivo, de_bytes, de_imagem

VERDE = (40, 160, 40)
MARROM = (30, 60, 110)


def test_vetor_tem_o_tamanho_declarado():
    vetor = de_imagem(imagem_solida(VERDE))

    assert vetor.shape == (N_CARACTERISTICAS,)
    assert N_CARACTERISTICAS == 96


def test_mesma_imagem_gera_o_mesmo_vetor():
    imagem = imagem_solida(VERDE)

    assert np.array_equal(de_imagem(imagem), de_imagem(imagem))


def test_cores_diferentes_geram_vetores_diferentes():
    verde = de_imagem(imagem_solida(VERDE))
    marrom = de_imagem(imagem_solida(MARROM))

    assert not np.array_equal(verde, marrom)


def test_bytes_invalidos_devolvem_none():
    assert de_bytes(b"isto nao e uma imagem") is None


def test_arquivo_inexistente_devolve_none(tmp_path):
    assert de_arquivo(tmp_path / "nao_existe.jpg") is None


def test_arquivo_e_bytes_dao_o_mesmo_vetor(tmp_path):
    caminho = tmp_path / "folha.png"
    cv2.imwrite(str(caminho), imagem_solida(VERDE))

    do_arquivo = de_arquivo(caminho)
    dos_bytes = de_bytes(caminho.read_bytes())

    assert np.array_equal(do_arquivo, dos_bytes)


def test_tamanho_da_imagem_nao_muda_o_vetor():
    """O vetor descreve proporcoes de cor, nao a resolucao da foto."""
    pequena = np.zeros((32, 32, 3), dtype=np.uint8)
    pequena[:, :] = VERDE
    grande = np.zeros((256, 256, 3), dtype=np.uint8)
    grande[:, :] = VERDE

    assert np.allclose(de_imagem(pequena), de_imagem(grande))
