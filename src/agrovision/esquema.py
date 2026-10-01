"""Contrato dos dados do AgroVision, em um unico lugar.

O aplicativo, o pipeline, a exportacao e os testes importam estes nomes.
Assim uma coluna nunca e escrita com um nome e lida com outro.
"""

NOME_IMAGEM = "nome_imagem"
CATEGORIA = "categoria"
ACURACIA = "acuracia"
DATA = "data"
LOCALIDADE = "localidade"
ORIGEM = "origem"

# Ordem das colunas em todo CSV e JSON que o projeto gera.
CAMPOS = [NOME_IMAGEM, CATEGORIA, ACURACIA, DATA, LOCALIDADE, ORIGEM]

# A coluna acuracia guarda a probabilidade que o modelo deu aquela imagem.
# Nao e a acuracia do modelo. O nome vem do enunciado da Fase 1 e foi mantido
# para que os arquivos das duas entregas continuem compativeis.
COLUNA_CONFIANCA = ACURACIA

SAUDAVEL = "Saudável"
DOENTE = "Doente"
CATEGORIAS_VALIDAS = [SAUDAVEL, DOENTE]

# Dois registros com o mesmo valor nestas tres colunas sao a mesma analise.
# A mesma folha pode ser fotografada de novo em outra data ou em outro talhao,
# e nesse caso conta como uma analise nova.
CHAVE_DEDUPLICACAO = [NOME_IMAGEM, DATA, LOCALIDADE]

OBRIGATORIAS = [NOME_IMAGEM, CATEGORIA, ACURACIA, DATA, LOCALIDADE]

# Verde para folha sadia, vermelho para folha doente. Com os dois tons de azul
# que a biblioteca de graficos usa por padrao, o leitor precisa conferir a
# legenda a cada grafico para saber qual serie e qual.
CORES = {SAUDAVEL: "#2E9E5B", DOENTE: "#D64545"}

ORIGEM_MODELO = "Modelo"
ORIGEM_LOTE = "Modelo (lote)"
ORIGEM_SIMULADO = "Simulado"

# Formato dos arquivos: ponto e virgula e BOM, para o Excel em portugues abrir
# o CSV com as colunas separadas e os acentos corretos.
SEPARADOR = ";"
CODIFICACAO = "utf-8-sig"
FORMATO_DATA = "%Y-%m-%d"

EXTENSOES_IMAGEM = {".jpg", ".jpeg", ".png"}

LOCALIDADES_PADRAO = ["Talhão A", "Talhão B", "Talhão C"]
