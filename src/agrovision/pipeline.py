"""Pipeline ETL do AgroVision: ingestao, transformacao e carga.

Tres camadas, no padrao medalhao:

- Bronze (data/saida/analises.csv): o que o modelo classificou, sem tratamento.
- Silver (data/saida/analises_tratadas.csv): tipos validados, registros
  invalidos e duplicados removidos. E a fonte do painel.
- Gold (data/saida/indicadores.json): indicadores agregados, prontos para
  consumo analitico.

Rode pela linha de comando com:
    python -m agrovision.pipeline
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from agrovision.esquema import (
    ACURACIA,
    CAMPOS,
    CATEGORIA,
    CATEGORIAS_VALIDAS,
    CHAVE_DEDUPLICACAO,
    CODIFICACAO,
    DATA,
    DOENTE,
    FORMATO_DATA,
    LOCALIDADE,
    OBRIGATORIAS,
    SAUDAVEL,
    SEPARADOR,
)
from agrovision.exportacao import escrever_csv, ler_csv

RAIZ = Path(__file__).resolve().parents[2]
SAIDA = RAIZ / "data" / "saida"
BRONZE = SAIDA / "analises.csv"
SILVER = SAIDA / "analises_tratadas.csv"
GOLD = SAIDA / "indicadores.json"


def acrescentar_bronze(registros: list[dict]) -> int:
    """Acrescenta analises a camada Bronze e devolve o total de registros.

    A Bronze aceita tudo, inclusive repeticao. A limpeza e trabalho da Silver.
    """
    historico = ler_csv(BRONZE) + list(registros)
    escrever_csv(BRONZE, historico)
    return len(historico)


def extrair() -> pd.DataFrame:
    """Ingestao: le a camada Bronze."""
    if not BRONZE.exists():
        print(f"[Extract] Nenhum dado bruto em {BRONZE}")
        return pd.DataFrame(columns=CAMPOS)

    df = pd.read_csv(BRONZE, sep=SEPARADOR, encoding=CODIFICACAO)
    print(f"[Extract] {len(df)} registro(s) lido(s) de {BRONZE.name}")
    return df


def transformar(df: pd.DataFrame) -> pd.DataFrame:
    """Transformacao: valida tipos, descarta invalidos e duplicados.

    Grava a camada Silver e devolve o DataFrame com a coluna de data em
    datetime, pronta para as agregacoes da camada Gold.
    """
    if df.empty:
        return df

    df = df.copy()
    df[DATA] = pd.to_datetime(df[DATA], errors="coerce")
    df[ACURACIA] = pd.to_numeric(df[ACURACIA], errors="coerce")

    antes = len(df)
    df = df.dropna(subset=OBRIGATORIAS)
    df = df[df[CATEGORIA].isin(CATEGORIAS_VALIDAS)]
    df = df.drop_duplicates(subset=CHAVE_DEDUPLICACAO)
    print(f"[Transform] {antes - len(df)} registro(s) descartado(s) na validacao")

    saida = df.copy()
    saida[DATA] = saida[DATA].dt.strftime(FORMATO_DATA)
    SAIDA.mkdir(parents=True, exist_ok=True)
    saida.to_csv(SILVER, sep=SEPARADOR, index=False, encoding=CODIFICACAO)
    print(f"[Transform] {len(saida)} registro(s) gravado(s) em {SILVER.name}")

    return df


def impressao_da_bronze() -> str:
    """Resumo do conteudo atual da camada Bronze."""
    if not BRONZE.exists():
        return ""

    return hashlib.sha256(BRONZE.read_bytes()).hexdigest()


def carregar(df: pd.DataFrame) -> dict:
    """Carga: calcula os indicadores agregados e grava a camada Gold."""
    agora = datetime.now().isoformat(timespec="seconds")

    if df.empty:
        indicadores = {
            "gerado_em": agora,
            "total_imagens": 0,
            "mensagem": "Sem dados tratados disponiveis.",
        }
    else:
        total = len(df)
        contagem = df[CATEGORIA].value_counts().to_dict()
        por_localidade = (
            df.groupby([LOCALIDADE, CATEGORIA])
            .size()
            .unstack(fill_value=0)
            .to_dict(orient="index")
        )
        tendencia = (
            df.groupby([df[DATA].dt.date, CATEGORIA]).size().unstack(fill_value=0)
        )
        tendencia.index = tendencia.index.astype(str)

        indicadores = {
            "gerado_em": agora,
            "total_imagens": total,
            "percentual_saudaveis": round(contagem.get(SAUDAVEL, 0) / total * 100, 2),
            "percentual_doentes": round(contagem.get(DOENTE, 0) / total * 100, 2),
            "confianca_media": round(float(df[ACURACIA].mean()), 2),
            "por_localidade": por_localidade,
            "tendencia_diaria": tendencia.to_dict(orient="index"),
        }

    # Guardada junto dos indicadores para garantir() saber se a Bronze mudou.
    indicadores["impressao_bronze"] = impressao_da_bronze()

    SAIDA.mkdir(parents=True, exist_ok=True)
    GOLD.write_text(
        json.dumps(indicadores, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[Load] Indicadores gravados em {GOLD.name}")

    return indicadores


def executar() -> dict:
    """Roda as tres camadas em sequencia."""
    print("=== Pipeline AgroVision: Bronze -> Silver -> Gold ===")
    indicadores = carregar(transformar(extrair()))
    print("=== Pipeline concluido ===")
    return indicadores


def garantir() -> bool:
    """Roda o pipeline somente se a Bronze mudou desde a ultima execucao.

    Evita reprocessar a cada interacao do painel. Devolve True se rodou.

    A comparacao usa o conteudo da Bronze, nao a data de modificacao dos
    arquivos. Duas gravacoes dentro do mesmo tique do relogio do sistema dao a
    mesma data, e nesse caso o painel continuaria mostrando dados velhos.
    """
    if not BRONZE.exists():
        return False

    if SILVER.exists() and GOLD.exists():
        try:
            gravado = json.loads(GOLD.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            gravado = {}

        if gravado.get("impressao_bronze") == impressao_da_bronze():
            return False

    executar()
    return True


def ler_camada(caminho: Path) -> pd.DataFrame:
    """Le uma camada como DataFrame, sem reprocessar nada."""
    if not caminho.exists():
        return pd.DataFrame(columns=CAMPOS)

    return pd.read_csv(caminho, sep=SEPARADOR, encoding=CODIFICACAO)


def limpar() -> None:
    """Apaga as tres camadas. Usado pelo botao de limpeza do painel."""
    for camada in (BRONZE, SILVER, GOLD):
        camada.unlink(missing_ok=True)


if __name__ == "__main__":
    executar()
