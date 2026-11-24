#Demonstracao sem broker: produtor e consumidor no mesmo processo, com filas em memoria

#Grava em data/saida/demonstracao para nunca misturar com os dados reais

import argparse

from agrovision import automacao, pipeline
from agrovision.streaming import produtor
from agrovision.streaming.consumidor import SENSORES, Consumidor
from agrovision.streaming.transporte import TransporteMemoria

DESCRICAO = "Demonstracao do streaming sem broker"


def executar(ticks: int = 16, ataque_a_cada: int = 0) -> Consumidor:
    saida = pipeline.SAIDA / automacao.DEMONSTRACAO
    with pipeline.em_saida(saida):
        saida.mkdir(parents=True, exist_ok=True)
        pipeline.limpar()
        (saida / SENSORES).unlink(missing_ok=True)

        transporte = TransporteMemoria()
        consumidor = Consumidor(transporte)
        simulador = produtor.Simulador()
        for _ in range(ticks):
            produtor.executar(transporte, 1, 0, 0, simulador, aviso=lambda *_: None)
            if ataque_a_cada and simulador.tick % ataque_a_cada == 0:
                tipo = produtor.ATAQUES[(simulador.tick // ataque_a_cada - 1) % 4]
                topico, evento = simulador.ataque(tipo)
                transporte.publicar(topico, evento)
            consumidor.ciclo(espera=0)
        consumidor.encerrar()
    return consumidor


def main(argumentos=None) -> None:
    leitor = argparse.ArgumentParser(description=DESCRICAO)
    leitor.add_argument("--ticks", type=int, default=16)
    leitor.add_argument("--ataque-a-cada", type=int, default=0)
    opcoes = leitor.parse_args(argumentos)

    consumidor = executar(opcoes.ticks, opcoes.ataque_a_cada)
    print(f"\nResumo: {dict(consumidor.contagem)} | rejeicoes: {dict(consumidor.motivos)}")


if __name__ == "__main__":
    main()
