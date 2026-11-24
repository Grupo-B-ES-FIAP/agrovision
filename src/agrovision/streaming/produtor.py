#Produtor do streaming: simula sensores e cameras do campo enviando eventos

#O Talhao B perde umidade e adoece a cada dia, para as regras dispararem sempre igual

import argparse
import random
import time
from datetime import date, timedelta

from agrovision.esquema import DOENTE, FORMATO_DATA, LOCALIDADES_PADRAO, SAUDAVEL
from agrovision.streaming import eventos
from agrovision.streaming.eventos import ANALISE, SENSOR

TICKS_POR_DIA = 4
ANALISES_POR_TICK = 2
DIA_INICIAL = date(2026, 9, 1)

# Probabilidade de folha doente no dia 0 e quanto cresce por dia.
DOENCA = {"Talhão A": (0.05, 0.0), "Talhão B": (0.05, 0.10), "Talhão C": (0.12, 0.0)}
UMIDADE = {"Talhão A": (55, 0), "Talhão B": (60, -5), "Talhão C": (50, 0)}

DESCRICAO = "Simula sensores e cameras do campo enviando eventos"

ATAQUES = ("adulterado", "replay", "dispositivo", "valor")


class Simulador:
    def __init__(self, semente: int = 42, dia_inicial: date = DIA_INICIAL, chave=None):
        self.sorteio = random.Random(semente)
        self.dia_inicial = dia_inicial
        self.chave = chave
        self.tick = 0
        self.contador = 0
        self.enviados: list[dict] = []

    @property
    def dia(self) -> int:
        return self.tick // TICKS_POR_DIA

    def _sensor(self, talhao: str) -> dict:
        base, queda = UMIDADE[talhao]
        carga = {
            "umidade_solo": round(max(10.0, base + queda * self.dia + self.sorteio.gauss(0, 2)), 1),
            "temperatura": round(self.sorteio.uniform(24, 31), 1),
        }
        return eventos.criar(SENSOR, talhao, carga, chave=self.chave)

    def _analise(self, talhao: str) -> dict:
        base, subida = DOENCA[talhao]
        doente = self.sorteio.random() < min(0.9, base + subida * self.dia)
        self.contador += 1
        data = (self.dia_inicial + timedelta(days=self.dia)).strftime(FORMATO_DATA)
        carga = {
            "nome_imagem": f"stream-{talhao[-1]}-{self.contador:05d}.jpg",
            "categoria": DOENTE if doente else SAUDAVEL,
            "acuracia": round(self.sorteio.uniform(80, 99), 1),
            "data": data,
        }
        return eventos.criar(ANALISE, talhao, carga, chave=self.chave)

    def proximo(self) -> list[tuple[str, dict]]:
        saida = []
        for talhao in LOCALIDADES_PADRAO:
            saida.append((eventos.TOPICO_SENSORES, self._sensor(talhao)))
            for _ in range(ANALISES_POR_TICK):
                saida.append((eventos.TOPICO_ANALISES, self._analise(talhao)))
        self.tick += 1
        self.enviados += [e for _, e in saida]
        return saida

    def ataque(self, tipo: str) -> tuple[str, dict]:
        talhao = LOCALIDADES_PADRAO[0]
        if tipo == "replay":
            # Copia exata de um evento ja enviado: assinatura valida, id repetido.
            copia = dict(self.enviados[0]) if self.enviados else self._sensor(talhao)
            return eventos.TOPICO_SENSORES, copia
        if tipo == "adulterado":
            evento = self._sensor(talhao)
            evento["carga"] = {**evento["carga"], "umidade_solo": 99.0}
            return eventos.TOPICO_SENSORES, evento
        if tipo == "dispositivo":
            # No clonado: assinatura correta, mas o dispositivo nao esta na lista.
            carga = {"umidade_solo": 50.0, "temperatura": 25.0}
            return eventos.TOPICO_SENSORES, eventos.criar(
                SENSOR, talhao, carga, dispositivo="sensor-clone-99", chave=self.chave
            )
        carga = {"umidade_solo": 250.0, "temperatura": 25.0}
        return eventos.TOPICO_SENSORES, eventos.criar(SENSOR, talhao, carga, chave=self.chave)


def executar(transporte, ticks: int, intervalo: float = 0, ataque_a_cada: int = 0,
             simulador: Simulador | None = None, aviso=print) -> int:
    simulador = simulador or Simulador()
    total = 0
    for i in range(1, ticks + 1):
        pacote = simulador.proximo()
        if ataque_a_cada and i % ataque_a_cada == 0:
            tipo = ATAQUES[(i // ataque_a_cada - 1) % len(ATAQUES)]
            pacote.append(simulador.ataque(tipo))
            aviso(f"[Produtor] tick {i}: injetando ataque '{tipo}'")

        for topico, evento in pacote:
            transporte.publicar(topico, evento)
        total += len(pacote)
        aviso(f"[Produtor] tick {i}/{ticks}: {len(pacote)} evento(s), dia {simulador.dia + 1}")
        if intervalo and i < ticks:
            time.sleep(intervalo)

    return total


def main(argumentos=None) -> None:
    from agrovision.streaming.transporte import TransporteKafka

    leitor = argparse.ArgumentParser(description=DESCRICAO)
    leitor.add_argument("--ticks", type=int, default=20)
    leitor.add_argument("--intervalo", type=float, default=1.0, help="segundos entre os ticks")
    leitor.add_argument("--ataque-a-cada", type=int, default=0, help="injeta evento malicioso")
    leitor.add_argument("--broker", help="host:porta (padrao: KAFKA_BROKER ou localhost:9092)")
    opcoes = leitor.parse_args(argumentos)

    transporte = TransporteKafka(opcoes.broker)
    try:
        total = executar(transporte, opcoes.ticks, opcoes.intervalo, opcoes.ataque_a_cada)
        print(f"[Produtor] {total} evento(s) enviados")
    finally:
        transporte.fechar()


if __name__ == "__main__":
    main()
