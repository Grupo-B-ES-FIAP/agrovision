#Transporte dos eventos: Kafka (Redpanda) em execucao real, memoria nos testes

#As duas classes tem a mesma interface, entao produtor e consumidor nao sabem qual usam


import json
import os
import socket
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
CONFIG_TOPICOS = RAIZ / "streaming" / "topicos.json"

BROKER_PADRAO = "localhost:9092"
GRUPO = "agrovision-consumidor"


def broker() -> str:
    return os.environ.get("KAFKA_BROKER", BROKER_PADRAO)


def broker_ativo(servidor: str | None = None, espera: float = 1.0) -> bool:
    #Teste de porta, sem depender do kafka-python
    host, _, porta = (servidor or broker()).rpartition(":")
    try:
        with socket.create_connection((host or "localhost", int(porta)), timeout=espera):
            return True
    except (OSError, ValueError):
        return False


class TransporteMemoria:
    #Filas em memoria. Serve para testes e para a demonstracao sem broker

    def __init__(self):
        self.filas = defaultdict(list)
        self._lidos = defaultdict(int)

    def publicar(self, topico: str, evento: dict) -> None:
        self.filas[topico].append(evento)

    def consumir(self, topicos: list[str], espera: float = 0) -> list[tuple[str, dict]]:
        lote = []
        for topico in topicos:
            lote += [(topico, e) for e in self.filas[topico][self._lidos[topico]:]]
            self._lidos[topico] = len(self.filas[topico])
        return lote

    def fechar(self) -> None:
        pass


class TransporteKafka:
    #Fala o protocolo Kafka, entao funciona com Redpanda ou Kafka sem mudar nada

    def __init__(self, servidor: str | None = None, consumir_de: list[str] | None = None):
        from kafka import KafkaConsumer, KafkaProducer

        self.servidor = servidor or broker()
        self.produtor = KafkaProducer(
            bootstrap_servers=self.servidor,
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode(),
            key_serializer=lambda chave: str(chave).encode(),
            acks="all",
        )
        self.consumidor = None
        if consumir_de:
            # O offset confirmado no grupo faz o papel do checkpoint da ingestao em lote.
            self.consumidor = KafkaConsumer(
                *consumir_de,
                bootstrap_servers=self.servidor,
                group_id=GRUPO,
                auto_offset_reset="earliest",
                value_deserializer=_decodificar,
            )

    def publicar(self, topico: str, evento: dict) -> None:
        # A chave e o dispositivo: as leituras de um sensor ficam em ordem na particao.
        self.produtor.send(topico, evento, key=str(evento.get("dispositivo", "sistema")))

    def consumir(self, topicos: list[str], espera: float = 1) -> list[tuple[str, dict]]:
        if self.consumidor is None:
            return []
        lidos = self.consumidor.poll(timeout_ms=int(espera * 1000))
        return [(p.topic, r.value) for p, registros in lidos.items() for r in registros]

    def fechar(self) -> None:
        self.produtor.flush()
        self.produtor.close()
        if self.consumidor:
            self.consumidor.close()


def _decodificar(dados: bytes | None):
    try:
        return json.loads(dados)
    except ValueError:
        return None


def criar_topicos(servidor: str | None = None) -> list[str]:
    #Cria os topicos de streaming/topicos.json que ainda nao existem.
    from kafka.admin import KafkaAdminClient, NewTopic
    from kafka.errors import TopicAlreadyExistsError

    config = json.loads(CONFIG_TOPICOS.read_text(encoding="utf-8"))["topicos"]
    admin = KafkaAdminClient(bootstrap_servers=servidor or broker())
    criados = []
    for item in config:
        topico = NewTopic(
            name=item["nome"],
            num_partitions=item["particoes"],
            replication_factor=item["replicas"],
            topic_configs={"retention.ms": str(item["retencao_ms"])},
        )
        try:
            admin.create_topics([topico])
            criados.append(item["nome"])
        except TopicAlreadyExistsError:
            pass
    admin.close()
    return criados


if __name__ == "__main__":
    print("Topicos criados:", ", ".join(criar_topicos()) or "nenhum (ja existiam)")
