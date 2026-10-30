"""Ingestao automatizada da Fase 3 (micro-batch).

Vigia a pasta data/entrada. Cada arquivo .csv ou .json novo tem os registros
ainda nao vistos gravados na Bronze, e o pipeline roda em seguida, chamando a
automacao. Sem registro novo, nada e acionado.

O checkpoint (data/saida/checkpoint.json) guarda o SHA-256 de cada arquivo lido.
Os registros sao comparados pela chave nome_imagem + data + localidade.

    python -m agrovision.ingestao            (vigia data/entrada)
    python -m agrovision.ingestao --uma-vez  (processa o que ha e sai)
    python -m agrovision.ingestao --demo     (data/entrada/demonstracao)
"""

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path

from agrovision import automacao, pipeline
from agrovision.decisao import REGRAS_DE_INTERVENCAO
from agrovision.esquema import (
    CAMPOS,
    CHAVE_DEDUPLICACAO,
    DATA,
    OBRIGATORIAS,
)
from agrovision.exportacao import ler_csv

RAIZ = Path(__file__).resolve().parents[2]
ENTRADA = RAIZ / "data" / "entrada"
ENTRADA_DEMO = ENTRADA / "demonstracao"

EXTENSOES = {".csv", ".json"}
INTERVALO_PADRAO = 5

PROCESSADO = "processado"
REJEITADO = "rejeitado"


def registrar(mensagem: str) -> None:
    """Escreve uma linha de log com a hora."""
    print(f"{datetime.now():%H:%M:%S} [Ingestao] {mensagem}")


def _chave(registro: dict) -> tuple:
    return tuple(str(registro.get(campo, "")).strip() for campo in CHAVE_DEDUPLICACAO)


def _impressao(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def ler_checkpoint() -> dict:
    """Le o checkpoint. Arquivo ausente ou corrompido recomeca do zero."""
    try:
        conteudo = json.loads(pipeline.CHECKPOINT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"arquivos": {}}

    if not isinstance(conteudo.get("arquivos"), dict):
        return {"arquivos": {}}
    return conteudo


def gravar_checkpoint(checkpoint: dict) -> None:
    """Grava por troca de arquivo, para o checkpoint nunca ficar pela metade."""
    checkpoint["atualizado_em"] = datetime.now().isoformat(timespec="seconds")
    pipeline.SAIDA.mkdir(parents=True, exist_ok=True)
    temporario = pipeline.CHECKPOINT.with_suffix(".tmp")
    temporario.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(pipeline.CHECKPOINT)


def listar_arquivos(pasta: Path) -> list[Path]:
    """Arquivos de dados da pasta, em ordem de nome. Ignora .tmp e subpastas."""
    if not pasta.is_dir():
        return []

    return sorted(
        arquivo
        for arquivo in pasta.iterdir()
        if arquivo.is_file() and arquivo.suffix.lower() in EXTENSOES
    )


def pendentes(pasta: Path, checkpoint: dict) -> list[Path]:
    """Arquivos que o checkpoint ainda nao conhece, ou que mudaram de conteudo."""
    lidos = checkpoint["arquivos"]
    return [
        arquivo
        for arquivo in listar_arquivos(pasta)
        if lidos.get(arquivo.name, {}).get("sha256") != _impressao(arquivo)
    ]


def ler_lote(caminho: Path) -> list[dict]:
    """Le um arquivo de entrada. O JSON aceita a lista ou o formato da exportacao."""
    if caminho.suffix.lower() == ".csv":
        return ler_csv(caminho)

    conteudo = json.loads(caminho.read_text(encoding="utf-8-sig"))
    if isinstance(conteudo, dict):
        conteudo = conteudo.get("resultados", [])
    if not isinstance(conteudo, list) or not all(isinstance(item, dict) for item in conteudo):
        raise ValueError("o JSON deve ser uma lista de registros ou ter a chave 'resultados'")
    return conteudo


def _validar_colunas(registros: list[dict]) -> None:
    ausentes = [campo for campo in OBRIGATORIAS if campo not in registros[0]] if registros else []
    if ausentes:
        raise ValueError("faltam as colunas " + ", ".join(ausentes))


def _ler_novos(arquivo: Path, vistos: set) -> tuple[list[dict], int]:
    """Registros do arquivo fora de `vistos` e quantos ja estavam. Atualiza `vistos`."""
    registros = ler_lote(arquivo)
    _validar_colunas(registros)

    novos, repetidos = [], 0
    for registro in registros:
        chave = _chave(registro)
        if chave in vistos:
            repetidos += 1
            continue
        vistos.add(chave)
        novos.append({campo: registro.get(campo, "") for campo in CAMPOS})

    return novos, repetidos


def _alertas_dos_dias(dias: set) -> list[dict]:
    """Decisoes de intervencao nos dias dos registros que acabaram de chegar."""
    try:
        alertas = json.loads(pipeline.ALERTAS.read_text(encoding="utf-8"))["alertas"]
    except (OSError, ValueError, KeyError):
        return []

    return [a for a in alertas if a["data"] in dias and a["regra"] in REGRAS_DE_INTERVENCAO]


def processar(pasta: Path = ENTRADA) -> dict:
    """Processa os arquivos novos da pasta, uma vez, e devolve um resumo."""
    checkpoint = ler_checkpoint()
    fila = pendentes(Path(pasta), checkpoint)
    resumo = {"arquivos": [], "novos": 0, "repetidos": 0, "alertas": []}

    if not fila:
        return resumo

    vistos = {_chave(r) for r in ler_csv(pipeline.BRONZE)}
    dias_novos = set()

    for arquivo in fila:
        try:
            impressao = _impressao(arquivo)
            novos, repetidos = _ler_novos(arquivo, vistos)
        except OSError as erro:
            # Ainda aberto por quem escreve: fica para o proximo ciclo.
            registrar(f"{arquivo.name}: nao foi possivel ler agora ({erro}). Tentarei de novo")
            continue
        except (ValueError, UnicodeDecodeError) as erro:
            checkpoint["arquivos"][arquivo.name] = {
                "sha256": _impressao(arquivo),
                "status": REJEITADO,
                "motivo": str(erro),
                "processado_em": datetime.now().isoformat(timespec="seconds"),
            }
            registrar(f"{arquivo.name}: REJEITADO ({erro})")
            resumo["arquivos"].append({"arquivo": arquivo.name, "status": REJEITADO})
            continue

        if novos:
            pipeline.acrescentar_bronze(novos)
        dias_novos |= {str(r[DATA]).strip()[:10] for r in novos}

        checkpoint["arquivos"][arquivo.name] = {
            "sha256": impressao,
            "status": PROCESSADO,
            "linhas": len(novos) + repetidos,
            "novos": len(novos),
            "processado_em": datetime.now().isoformat(timespec="seconds"),
        }
        registrar(
            f"{arquivo.name}: {len(novos) + repetidos} linha(s), "
            f"{len(novos)} nova(s), {repetidos} ja processada(s)"
        )
        resumo["arquivos"].append({"arquivo": arquivo.name, "status": PROCESSADO})
        resumo["novos"] += len(novos)
        resumo["repetidos"] += repetidos

    gravar_checkpoint(checkpoint)

    if resumo["novos"]:
        registrar(f"{resumo['novos']} registro(s) novo(s). Rodando pipeline e regras de decisao")
        pipeline.executar()
        resumo["alertas"] = _alertas_dos_dias(dias_novos)
        for a in resumo["alertas"]:
            registrar(
                f"ALERTA {a['talhao']} {a['data']} {a['percentual_doentes']:.1f}% "
                f"{a['regra']} {a['nivel']}: {a['recomendacao']}"
            )
        registrar(f"Alertas e relatorio atualizados em {pipeline.SAIDA}")
    elif resumo["arquivos"]:
        registrar("Nenhum registro novo. Pipeline e automacao nao foram acionados")

    return resumo


def monitorar(pasta: Path = ENTRADA, intervalo: float = INTERVALO_PADRAO, ciclos=None) -> None:
    """Chama processar() a cada `intervalo` segundos. `ciclos` limita as repeticoes."""
    registrar(f"Vigiando {pasta} a cada {intervalo:g}s. Ctrl+C para encerrar")
    ocioso = False
    ciclo = 0

    while ciclos is None or ciclo < ciclos:
        ciclo += 1
        resumo = processar(pasta)

        if resumo["arquivos"]:
            ocioso = False
        elif not ocioso:
            registrar("Sem arquivos novos. Aguardando")
            ocioso = True

        if ciclos is None or ciclo < ciclos:
            time.sleep(intervalo)


def main(argumentos=None) -> None:
    leitor = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    leitor.add_argument("--demo", action="store_true", help="usa a pasta e a saida de demonstracao")
    leitor.add_argument("--pasta", type=Path, help="pasta vigiada (padrao: data/entrada)")
    leitor.add_argument("--uma-vez", action="store_true", help="processa o que ha e encerra")
    leitor.add_argument("--intervalo", type=float, default=INTERVALO_PADRAO,
                        help="segundos entre as verificacoes")
    opcoes = leitor.parse_args(argumentos)

    pasta = opcoes.pasta or (ENTRADA_DEMO if opcoes.demo else ENTRADA)
    pasta.mkdir(parents=True, exist_ok=True)

    # Simulado nunca se mistura com o real.
    saida = pipeline.SAIDA / automacao.DEMONSTRACAO if opcoes.demo else pipeline.SAIDA

    with pipeline.em_saida(saida):
        try:
            if opcoes.uma_vez:
                if not processar(pasta)["arquivos"]:
                    lidos = len(ler_checkpoint()["arquivos"])
                    registrar(f"Nenhum arquivo novo. {lidos} arquivo(s) ja constam no checkpoint")
            else:
                monitorar(pasta, opcoes.intervalo)
        except KeyboardInterrupt:
            registrar("Encerrado pelo usuario")


if __name__ == "__main__":
    main()
