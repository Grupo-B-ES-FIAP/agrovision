#Consumidor do streaming: valida os eventos e alimenta o pipeline e as regras

import argparse
import json
import time
from collections import Counter, deque
from datetime import datetime

from agrovision import automacao, pipeline
from agrovision.decisao import REGRAS_DE_INTERVENCAO
from agrovision.esquema import LOCALIDADES_PADRAO, ORIGEM_SIMULADO
from agrovision.streaming import eventos
from agrovision.streaming.eventos import ANALISE, EventoInvalido

ESTADO = "streaming_estado.json"
SENSORES = "sensores.jsonl"

LIMITE_UMIDADE = 30.0
LIMITE_TEMPERATURA = 35.0
LOTE_ANALISES = 6
IDS_LEMBRADOS = 10_000
RECENTES = 15

DESCRICAO = "Consome os eventos, valida e alimenta o pipeline e as regras"


def registrar(mensagem: str) -> None:
    print(f"{datetime.now():%H:%M:%S} [Consumidor] {mensagem}")


class Consumidor:
    def __init__(self, transporte, lote_analises: int = LOTE_ANALISES, chave=None, agora=None):
        self.transporte = transporte
        self.lote_analises = lote_analises
        self.chave = chave
        self.agora = agora or time.time
        self.vistos: deque[str] = deque(maxlen=IDS_LEMBRADOS)
        self._vistos_busca: set[str] = set()
        self.pendentes: list[dict] = []
        self.sensor_ativo: set[tuple] = set()
        self.alertas_emitidos: set[tuple] = set()
        self.contagem = Counter()
        self.motivos = Counter()
        self.recentes: deque[dict] = deque(maxlen=RECENTES)
        self.rejeicoes: deque[dict] = deque(maxlen=RECENTES)
        self.alertas: deque[dict] = deque(maxlen=RECENTES)
        self.ultima_umidade: dict[str, float] = {}

    def _lembrar(self, identificador: str) -> bool:
        if identificador in self._vistos_busca:
            return False
        if len(self.vistos) == self.vistos.maxlen:
            self._vistos_busca.discard(self.vistos[0])
        self.vistos.append(identificador)
        self._vistos_busca.add(identificador)
        return True

    def tratar(self, evento) -> bool:
        self.contagem["recebidos"] += 1
        try:
            eventos.validar(evento, self.chave, self.agora())
            if not self._lembrar(evento["id"]):
                raise EventoInvalido("repetido", "id ja processado (replay)")
        except EventoInvalido as erro:
            self._rejeitar(evento, erro)
            return False

        self.contagem["aceitos"] += 1
        self.recentes.appendleft(
            {"hora": datetime.now().strftime("%H:%M:%S"), "tipo": evento["tipo"],
             "talhao": evento["talhao"], "dispositivo": evento["dispositivo"], **evento["carga"]}
        )
        if evento["tipo"] == ANALISE:
            self._receber_analise(evento)
        else:
            self._receber_sensor(evento)
        return True

    def _rejeitar(self, evento, erro: EventoInvalido) -> None:
        self.contagem["rejeitados"] += 1
        self.motivos[erro.codigo] += 1
        origem = evento.get("dispositivo", "?") if isinstance(evento, dict) else "?"
        item = {"hora": datetime.now().strftime("%H:%M:%S"), "codigo": erro.codigo,
                "motivo": str(erro), "dispositivo": origem}
        self.rejeicoes.appendleft(item)
        self.transporte.publicar(eventos.TOPICO_REJEITADOS, item)
        registrar(f"REJEITADO ({erro.codigo}) {origem}: {erro}")

    def _receber_sensor(self, evento: dict) -> None:
        carga, talhao = evento["carga"], evento["talhao"]
        self.ultima_umidade[talhao] = carga["umidade_solo"]

        with (pipeline.SAIDA / SENSORES).open("a", encoding="utf-8") as arquivo:
            registro = {"ts": evento["ts"], "talhao": talhao, **carga}
            arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")

        limites = (
            ("S1", carga["umidade_solo"] < LIMITE_UMIDADE,
             f"Umidade do solo em {carga['umidade_solo']}% (minimo {LIMITE_UMIDADE:g}%). Irrigar."),
            ("S2", carga["temperatura"] > LIMITE_TEMPERATURA,
             f"Temperatura em {carga['temperatura']} C (maximo {LIMITE_TEMPERATURA:g} C)."),
        )
        for regra, violada, mensagem in limites:
            chave = (talhao, regra)
            if violada and chave not in self.sensor_ativo:
                self.sensor_ativo.add(chave)
                self._alertar({"origem": "sensor", "talhao": talhao, "regra": regra,
                               "nivel": "Crítico", "mensagem": mensagem})
            elif not violada:
                # Voltou ao normal: um novo desvio gera novo alerta.
                self.sensor_ativo.discard(chave)

    def _receber_analise(self, evento: dict) -> None:
        carga = evento["carga"]
        self.pendentes.append({
            "nome_imagem": carga["nome_imagem"], "categoria": carga["categoria"],
            "acuracia": carga["acuracia"], "data": carga["data"],
            "localidade": evento["talhao"], "origem": ORIGEM_SIMULADO,
        })
        if len(self.pendentes) >= self.lote_analises:
            self.fechar_lote()

    def fechar_lote(self) -> None:
        if not self.pendentes:
            return

        lote, self.pendentes = self.pendentes, []
        dias = {r["data"] for r in lote}
        pipeline.acrescentar_bronze(lote)
        registrar(f"{len(lote)} analise(s) na Bronze. Rodando pipeline e regras de decisao")
        pipeline.executar()

        try:
            decisoes = json.loads(pipeline.ALERTAS.read_text(encoding="utf-8"))["alertas"]
        except (OSError, ValueError, KeyError):
            return

        for d in decisoes:
            chave = (d["talhao"], d["data"], d["regra"], d["nivel"])
            if d["data"] in dias and d["regra"] in REGRAS_DE_INTERVENCAO \
                    and chave not in self.alertas_emitidos:
                self.alertas_emitidos.add(chave)
                self._alertar({
                    "origem": "analise", "talhao": d["talhao"], "regra": d["regra"],
                    "nivel": d["nivel"], "data": d["data"],
                    "mensagem": f"{d['percentual_doentes']:.1f}% de folhas doentes. "
                                f"{d['recomendacao']}",
                })

    def _alertar(self, alerta: dict) -> None:
        alerta["hora"] = datetime.now().strftime("%H:%M:%S")
        self.alertas.appendleft(alerta)
        self.contagem["alertas"] += 1
        self.transporte.publicar(eventos.TOPICO_ALERTAS, alerta)
        registrar(f"ALERTA {alerta['talhao']} {alerta['regra']} {alerta['nivel']}: "
                  f"{alerta['mensagem']}")

    def gravar_estado(self) -> None:
        #Grava por troca de arquivo, para o painel nunca ler o JSON pela metade
        estado = {
            "atualizado_em": datetime.now().isoformat(timespec="seconds"),
            "contagem": dict(self.contagem),
            "motivos_rejeicao": dict(self.motivos),
            "umidade_por_talhao": {t: self.ultima_umidade.get(t) for t in LOCALIDADES_PADRAO},
            "eventos": list(self.recentes),
            "rejeicoes": list(self.rejeicoes),
            "alertas": list(self.alertas),
        }
        pipeline.SAIDA.mkdir(parents=True, exist_ok=True)
        destino = pipeline.SAIDA / ESTADO
        temporario = destino.with_suffix(".tmp")
        temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
        temporario.replace(destino)

    def ciclo(self, espera: float = 1) -> int:
        lidos = self.transporte.consumir(eventos.TOPICOS_ENTRADA, espera)
        for _, evento in lidos:
            self.tratar(evento)
        if lidos:
            self.gravar_estado()
        return len(lidos)

    def encerrar(self) -> None:
        self.fechar_lote()
        self.gravar_estado()


def main(argumentos=None) -> None:
    from agrovision.streaming.transporte import TransporteKafka

    leitor = argparse.ArgumentParser(description=DESCRICAO)
    leitor.add_argument("--demo", action="store_true", help="grava em data/saida/demonstracao")
    leitor.add_argument("--broker", help="host:porta (padrao: KAFKA_BROKER ou localhost:9092)")
    leitor.add_argument("--lote", type=int, default=LOTE_ANALISES,
                        help="analises por execucao do pipeline")
    opcoes = leitor.parse_args(argumentos)

    saida = pipeline.SAIDA / automacao.DEMONSTRACAO if opcoes.demo else pipeline.SAIDA
    transporte = TransporteKafka(opcoes.broker, consumir_de=eventos.TOPICOS_ENTRADA)

    with pipeline.em_saida(saida):
        saida.mkdir(parents=True, exist_ok=True)
        consumidor = Consumidor(transporte, opcoes.lote)
        registrar(f"Consumindo {', '.join(eventos.TOPICOS_ENTRADA)}. Ctrl+C para encerrar")
        try:
            while True:
                consumidor.ciclo(espera=1)
        except KeyboardInterrupt:
            registrar("Encerrado pelo usuario")
        finally:
            consumidor.encerrar()
            transporte.fechar()


if __name__ == "__main__":
    main()
