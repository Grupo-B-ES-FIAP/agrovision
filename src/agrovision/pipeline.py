from pathlib import Path
from datetime import datetime
import json

import pandas as pd

from agrovision.exportacao import CAMPOS

RAIZ = Path(__file__).resolve().parents[2]
DADOS = RAIZ / "data" / "saida"
ARQUIVO_BRUTO = DADOS / "analises.csv"
ARQUIVO_TRATADO = DADOS / "analises_tratadas.csv"
ARQUIVO_INDICADORES = DADOS / "indicadores.json"


def extrair():
    #Ingestão (Bronze): lê os dados brutos gerados pelo app.py
    if not ARQUIVO_BRUTO.exists():
        print("[Extract] Nenhum dado bruto encontrado em", ARQUIVO_BRUTO)
        return pd.DataFrame(columns=CAMPOS)
    df = pd.read_csv(ARQUIVO_BRUTO, sep=";", encoding="utf-8-sig")
    print(f"[Extract] {len(df)} registros lidos de {ARQUIVO_BRUTO.name}")
    return df


def transformar(df):
    #Transformação (Silver): valida tipos, remove inválidos e duplicados
    if df.empty:
        return df
    df = df.copy()
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["acuracia"] = pd.to_numeric(df["acuracia"], errors="coerce")

    antes = len(df)
    df = df.dropna(subset=["nome_imagem", "categoria", "data", "acuracia", "localidade"])
    df = df[df["categoria"].isin(["Saudável", "Doente"])]
    df = df.drop_duplicates(subset=["nome_imagem", "data", "localidade"])
    print(f"[Transform] {antes - len(df)} registro(s) descartado(s) na validação")

    DADOS.mkdir(parents=True, exist_ok=True)
    saida = df.copy()
    saida["data"] = saida["data"].dt.strftime("%Y-%m-%d")
    saida.to_csv(ARQUIVO_TRATADO, sep=";", index=False, encoding="utf-8-sig")
    print(f"[Transform] Dados tratados salvos em {ARQUIVO_TRATADO.name}")
    return df


def carregar(df):
    #Carga (Gold): indicadores agregados prontos para consumo analítico
    agora = datetime.now().isoformat(timespec="seconds")
    if df.empty:
        indicadores = {"gerado_em": agora, "total_imagens": 0,
                       "mensagem": "Sem dados tratados disponíveis."}
    else:
        total = len(df)
        contagem = df["categoria"].value_counts().to_dict()
        saudaveis, doentes = contagem.get("Saudável", 0), contagem.get("Doente", 0)
        por_localidade = (df.groupby(["localidade", "categoria"]).size()
                          .unstack(fill_value=0).to_dict(orient="index"))
        tendencia = df.groupby([df["data"].dt.date, "categoria"]).size().unstack(fill_value=0)
        tendencia.index = tendencia.index.astype(str)
        indicadores = {"gerado_em": agora, "total_imagens": total,
                       "percentual_saudaveis": round(saudaveis / total * 100, 2),
                       "percentual_doentes": round(doentes / total * 100, 2),
                       "confianca_media": round(float(df["acuracia"].mean()), 2),
                       "por_localidade": por_localidade,
                       "tendencia_diaria": tendencia.to_dict(orient="index")}
    DADOS.mkdir(parents=True, exist_ok=True)
    with ARQUIVO_INDICADORES.open("w", encoding="utf-8") as arquivo:
        json.dump(indicadores, arquivo, ensure_ascii=False, indent=2)
    print(f"[Load] Indicadores salvos em {ARQUIVO_INDICADORES.name}")
    return indicadores


def executar_pipeline():
    print("=== Pipeline de integração de dados — AgroVision ===")
    indicadores = carregar(transformar(extrair()))
    print("=== Pipeline concluído ===")
    return indicadores


def garantir_pipeline():
    #Roda o pipeline só se a camada Silver estiver desatualizada em relação à Bronze.
    if not ARQUIVO_BRUTO.exists():
        return False
    if ARQUIVO_TRATADO.exists() and ARQUIVO_TRATADO.stat().st_mtime >= ARQUIVO_BRUTO.stat().st_mtime:
        return False
    executar_pipeline()
    return True


if __name__ == "__main__":
    executar_pipeline()