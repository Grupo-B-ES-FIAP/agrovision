"""Testes isolados do motor de decisões; não alteram os dados reais."""
from datetime import date, timedelta
from motor_decisao import avaliar


def criar_registros(talhao, dia, total, doentes):
    return [
        {"data": dia.isoformat(), "localidade": talhao,
         "categoria": "Doente" if i < doentes else "Saudável"}
        for i in range(total)
    ]


def testar():
    inicio = date(2026, 10, 20)
    dados = []
    dados += criar_registros("Teste R1", inicio, 10, 0)
    dados += criar_registros("Teste R2", inicio, 10, 2)
    dados += criar_registros("Teste R3", inicio, 10, 4)
    for i in range(3):
        dados += criar_registros("Teste R4", inicio + timedelta(days=i), 10, 2)
        dados += criar_registros("Teste R5", inicio + timedelta(days=i), 10, 5)
    resultados = avaliar(dados)
    esperados = {"Teste R1": "R1", "Teste R2": "R2", "Teste R3": "R3",
                 "Teste R4": "R4", "Teste R5": "R5"}
    print("===== TESTES AGROVISION FASE 3 =====")
    for talhao, esperado in esperados.items():
        registros = [r for r in resultados if r["talhao"] == talhao]
        ultimo = registros[-1]
        passou = ultimo["regra"] == esperado
        print(f"{talhao}: {ultimo['regra']} | {ultimo['nivel']} | "
              f"{'APROVADO' if passou else 'FALHOU'}")
        assert passou, f"Falha em {talhao}: esperado {esperado}, recebido {ultimo['regra']}"
    print("TODAS AS 5 REGRAS FORAM APROVADAS!")


if __name__ == "__main__":
    testar()
