import csv
import sys
from datetime import date
from pathlib import Path

import cv2
import joblib
import numpy as np

from agrovision.exportacao import CAMPOS

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "models" / "modelo_folhas.pkl"
HISTORICO = RAIZ / "data" / "saida" / "analises.csv"
EXTENSOES_VALIDAS = {".jpg", ".jpeg", ".png"}


def extrair_caracteristicas(caminho_imagem):
    imagem = cv2.imread(str(caminho_imagem))
    if imagem is None:
        return None
    hsv = cv2.cvtColor(cv2.resize(imagem, (128, 128)), cv2.COLOR_BGR2HSV)
    histogramas = []
    for canal, limites in [(0, 180), (1, 256), (2, 256)]:
        hist = cv2.calcHist([hsv], [canal], None, [32], [0, limites])
        histogramas.append(cv2.normalize(hist, hist).flatten())
    return np.concatenate(histogramas)


def carregar_historico_existente():
    if not HISTORICO.exists():
        return []
    with HISTORICO.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def salvar_historico(registros):
    HISTORICO.parent.mkdir(parents=True, exist_ok=True)
    with HISTORICO.open("w", encoding="utf-8-sig", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=CAMPOS, delimiter=";")
        escritor.writeheader()
        escritor.writerows(registros)


def importar(pasta, localidade, data_coleta):
    modelo = joblib.load(MODELO)
    historico = carregar_historico_existente()
    novos = 0

    for caminho in Path(pasta).iterdir():
        if caminho.suffix.lower() not in EXTENSOES_VALIDAS:
            continue
        caracteristicas = extrair_caracteristicas(caminho)
        if caracteristicas is None:
            print(f"Aviso: não foi possível ler {caminho.name}")
            continue
        entrada = caracteristicas.reshape(1, -1)
        previsao = modelo.predict(entrada)[0]
        categoria = "Saudável" if previsao == 0 else "Doente"
        confianca = round(float(max(modelo.predict_proba(entrada)[0]) * 100), 2)
        historico.append({"nome_imagem": caminho.name, "categoria": categoria,
                          "acuracia": confianca, "data": data_coleta,
                          "localidade": localidade, "origem": "Modelo (lote)"})
        novos += 1
        print(f"{caminho.name}: {categoria} ({confianca:.2f}%)")

    if novos:
        salvar_historico(historico)
        print(f"\n{novos} nova(s) imagem(ns) adicionada(s) à base {HISTORICO}")
    else:
        print("Nenhuma imagem nova encontrada na pasta informada.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python importar_novas_imagens.py <pasta> <localidade> [data AAAA-MM-DD]")
        sys.exit(1)
    importar(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else date.today().isoformat())