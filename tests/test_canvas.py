#Testes do Canvas: nove blocos preenchidos e dispostos no quadro

from agrovision import canvas


def test_os_nove_blocos_do_bmc_estao_preenchidos():
    esperados = {"parcerias", "atividades", "recursos", "proposta", "relacionamento",
                 "canais", "segmentos", "custos", "receitas"}
    assert set(canvas.BLOCOS) == esperados
    assert all(len(bloco["itens"]) >= 3 for bloco in canvas.BLOCOS.values())


def test_receita_e_segmento_marcam_o_que_e_hipotese():
    assert any("(H)" in item for item in canvas.BLOCOS["receitas"]["itens"])
    assert any("(H)" in item for item in canvas.BLOCOS["segmentos"]["itens"])


def test_cada_hipotese_tem_teste_e_indicador():
    assert all(len(h) == 3 and all(h) for h in canvas.HIPOTESES)


def test_disposicao_usa_cada_bloco_uma_vez():
    usados = [chave for _, colunas in canvas.DISPOSICAO for coluna in colunas for chave in coluna]
    assert sorted(usados) == sorted(canvas.BLOCOS)
    assert all(len(pesos) == len(colunas) for pesos, colunas in canvas.DISPOSICAO)
