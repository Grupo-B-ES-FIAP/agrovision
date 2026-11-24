#Contrato e seguranca dos eventos: assinatura HMAC-SHA256 conferida pelo consumidor

import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime

from agrovision.esquema import (
    CATEGORIAS_VALIDAS,
    FORMATO_DATA,
    LOCALIDADES_PADRAO,
)

TOPICO_SENSORES = "agrovision.sensores"
TOPICO_ANALISES = "agrovision.analises"
TOPICO_ALERTAS = "agrovision.alertas"
TOPICO_REJEITADOS = "agrovision.rejeitados"
TOPICOS_ENTRADA = [TOPICO_SENSORES, TOPICO_ANALISES]

SENSOR = "sensor"
ANALISE = "analise"

# Evento mais velho que isto e tratado como replay.
JANELA_SEGUNDOS = 300

SEGREDO_PADRAO = "agrovision-dev"

# Faixas fisicamente possiveis. Fora delas, o sensor esta com defeito ou foi forjado.
LIMITES_SENSOR = {"umidade_solo": (0, 100), "temperatura": (-10, 60)}


def segredo() -> str:
    #Chave compartilhada. Em producao vem do ambiente, nunca do codigo
    return os.environ.get("AGROVISION_SEGREDO", SEGREDO_PADRAO)


def dispositivo_de(tipo: str, talhao: str) -> str:
    return f"{'sensor' if tipo == SENSOR else 'camera'}-{talhao[-1].lower()}"


DISPOSITIVOS_AUTORIZADOS = {
    dispositivo_de(tipo, talhao) for tipo in (SENSOR, ANALISE) for talhao in LOCALIDADES_PADRAO
}


class EventoInvalido(ValueError):

    def __init__(self, codigo: str, motivo: str):
        super().__init__(motivo)
        self.codigo = codigo


def _corpo(evento: dict) -> bytes:
    sem_assinatura = {k: v for k, v in evento.items() if k != "assinatura"}
    return json.dumps(sem_assinatura, sort_keys=True, separators=(",", ":")).encode()


def assinar(evento: dict, chave: str | None = None) -> dict:
    chave = chave or segredo()
    evento["assinatura"] = hmac.new(chave.encode(), _corpo(evento), hashlib.sha256).hexdigest()
    return evento


def criar(tipo: str, talhao: str, carga: dict, ts: float | None = None,
          dispositivo: str | None = None, chave: str | None = None) -> dict:
    return assinar(
        {
            "id": uuid.uuid4().hex,
            "tipo": tipo,
            "dispositivo": dispositivo or dispositivo_de(tipo, talhao),
            "talhao": talhao,
            "ts": ts if ts is not None else time.time(),
            "carga": carga,
        },
        chave,
    )


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _validar_carga(tipo: str, carga: dict) -> None:
    if tipo == SENSOR:
        for campo, (minimo, maximo) in LIMITES_SENSOR.items():
            valor = carga.get(campo)
            if not _numero(valor) or not minimo <= valor <= maximo:
                raise EventoInvalido("esquema", f"{campo} invalido: {valor!r}")
        return

    if not isinstance(carga.get("nome_imagem"), str) or not carga["nome_imagem"]:
        raise EventoInvalido("esquema", "nome_imagem ausente")
    if carga.get("categoria") not in CATEGORIAS_VALIDAS:
        raise EventoInvalido("esquema", f"categoria invalida: {carga.get('categoria')!r}")
    if not _numero(carga.get("acuracia")) or not 0 <= carga["acuracia"] <= 100:
        raise EventoInvalido("esquema", f"acuracia invalida: {carga.get('acuracia')!r}")
    try:
        datetime.strptime(str(carga.get("data")), FORMATO_DATA)
    except ValueError:
        raise EventoInvalido("esquema", f"data invalida: {carga.get('data')!r}") from None


def validar(evento, chave: str | None = None, agora: float | None = None) -> dict:
    if not isinstance(evento, dict):
        raise EventoInvalido("esquema", "evento nao e um objeto")

    faltam = [c for c in ("id", "tipo", "dispositivo", "talhao", "ts", "carga", "assinatura")
              if c not in evento]
    if faltam or not isinstance(evento["carga"], dict) or not _numero(evento["ts"]):
        raise EventoInvalido("esquema", "campos ausentes: " + ", ".join(faltam or ["carga/ts"]))

    # A assinatura vem primeiro: nada do conteudo e confiavel antes dela.
    esperado = hmac.new((chave or segredo()).encode(), _corpo(evento), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(esperado, str(evento["assinatura"])):
        raise EventoInvalido("assinatura", "assinatura nao confere")

    if evento["tipo"] not in (SENSOR, ANALISE) or evento["talhao"] not in LOCALIDADES_PADRAO:
        raise EventoInvalido("esquema", "tipo ou talhao desconhecido")
    if evento["dispositivo"] not in DISPOSITIVOS_AUTORIZADOS:
        raise EventoInvalido("dispositivo", f"dispositivo nao autorizado: {evento['dispositivo']}")

    idade = (agora if agora is not None else time.time()) - evento["ts"]
    if abs(idade) > JANELA_SEGUNDOS:
        raise EventoInvalido("expirado", f"evento fora da janela de {JANELA_SEGUNDOS}s")

    _validar_carga(evento["tipo"], evento["carga"])
    return evento
