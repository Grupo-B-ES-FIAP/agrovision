"""Testes do motor de decisoes: uma regra por cenario, mais os casos de borda."""

from datetime import date, timedelta

import pytest

from agrovision.decisao import avaliar, situacao_atual

INICIO = date(2026, 10, 20)


def folhas(talhao, dia, total, doentes):
    """Monta `total` registros de um talhao e dia, `doentes` deles doentes."""
    return [
        {
            "data": dia.isoformat(),
            "localidade": talhao,
            "categoria": "Doente" if i < doentes else "Saudável",
        }
        for i in range(total)
    ]


def dias_seguidos(talhao, quantidade, total, doentes):
    registros = []
    for i in range(quantidade):
        registros += folhas(talhao, INICIO + timedelta(days=i), total, doentes)
    return registros


def ultima_regra(registros):
    return avaliar(registros)[-1]["regra"]


@pytest.mark.parametrize(
    ("registros", "esperada"),
    [
        (folhas("T", INICIO, 10, 0), "R1"),
        (folhas("T", INICIO, 10, 2), "R2"),
        (folhas("T", INICIO, 10, 4), "R3"),
        (dias_seguidos("T", 3, 10, 2), "R4"),
        (dias_seguidos("T", 3, 10, 5), "R5"),
    ],
    ids=["R1 normal", "R2 atencao", "R3 critico", "R4 persistencia", "R5 prioridade"],
)
def test_cada_regra(registros, esperada):
    assert ultima_regra(registros) == esperada


def test_limiares_sao_exclusivos():
    assert ultima_regra(folhas("T", INICIO, 10, 1)) == "R1"
    assert ultima_regra(folhas("T", INICIO, 10, 3)) == "R2"


def test_dia_sem_dados_quebra_a_persistencia():
    registros = folhas("T", INICIO, 10, 2) + folhas("T", INICIO + timedelta(days=2), 10, 2)
    registros += folhas("T", INICIO + timedelta(days=3), 10, 2)

    assert ultima_regra(registros) == "R2"


def test_dia_sem_doente_quebra_a_persistencia():
    registros = dias_seguidos("T", 2, 10, 2) + folhas("T", INICIO + timedelta(days=2), 10, 0)

    assert ultima_regra(registros) == "R1"


def test_talhoes_sao_avaliados_separadamente():
    registros = []
    for i in range(3):
        talhao = "A" if i % 2 == 0 else "B"
        registros += folhas(talhao, INICIO + timedelta(days=i), 10, 2)

    assert {a["regra"] for a in avaliar(registros)} == {"R2"}


def test_ignora_data_e_categoria_invalidas():
    registros = folhas("T", INICIO, 10, 0) + [
        {"data": "ontem", "localidade": "T", "categoria": "Doente"},
        {"data": INICIO.isoformat(), "localidade": "T", "categoria": "Talvez"},
    ]

    [alerta] = avaliar(registros)
    assert (alerta["total"], alerta["regra"]) == (10, "R1")


def test_operadores_booleanos_no_alerta():
    alerta = avaliar(dias_seguidos("T", 3, 10, 2))[-1]

    assert alerta["persistencia_3_dias"] is True
    assert alerta["controle_recomendado"] is True
    assert alerta["situacao_normal"] is False


def test_situacao_atual_pega_o_ultimo_dia_de_cada_talhao():
    registros = folhas("A", INICIO, 10, 5) + folhas("A", INICIO + timedelta(days=1), 10, 0)
    registros += folhas("B", INICIO, 10, 2)

    atual = situacao_atual(avaliar(registros))

    assert [(a["talhao"], a["regra"]) for a in atual] == [("A", "R1"), ("B", "R2")]
