#Business Model Canvas do AgroSmart: conteudo desenhado pela aba Modelo de negocio do painel

#Itens marcados com (H) sao hipoteses a validar com o mercado, nao fatos

# Disposicao do quadro: cada linha tem colunas, e cada coluna empilha blocos
DISPOSICAO = [
    ([1, 1, 1.2, 1, 1], [["parcerias"], ["atividades", "recursos"], ["proposta"],
                         ["relacionamento", "canais"], ["segmentos"]]),
    ([1, 1], [["custos"], ["receitas"]]),
]

BLOCOS = {
    "parcerias": {
        "titulo": "Parcerias-chave",
        "itens": [
            "Cooperativas e associações de produtores",
            "Revendas de insumos agrícolas",
            "Fabricantes de sensores e câmeras de campo",
            "Agrônomos e instituições de pesquisa, para validar as regras",
            "Provedor de nuvem e de conectividade rural",
        ],
    },
    "atividades": {
        "titulo": "Atividades-chave",
        "itens": [
            "Treinar e atualizar o modelo de visão",
            "Operar o pipeline de streaming e os alertas",
            "Validar as regras de decisão com agrônomos",
            "Onboarding e suporte ao produtor",
            "Integrar sensores e câmeras de novos parceiros",
        ],
    },
    "recursos": {
        "titulo": "Recursos-chave",
        "itens": [
            "Modelo de visão computacional e base de imagens",
            "Plataforma de streaming em contêineres",
            "Regras de decisão R1 a R5 e limites de sensor",
            "Equipe de dados, IA e desenvolvimento",
            "Confiança dos produtores e dos parceiros",
        ],
    },
    "proposta": {
        "titulo": "Proposta de valor",
        "itens": [
            "Descobre a doença cedo: a foto da folha vira diagnóstico na hora",
            "Mostra em qual talhão o problema cresce, e não só que ele existe",
            "Alerta de umidade crítica e de doença persistente em tempo real",
            "Defensivo e água só onde precisa, com ação recomendada clara",
            "Dados assinados e validados: alerta em que se pode confiar",
        ],
    },
    "relacionamento": {
        "titulo": "Relacionamento com clientes",
        "itens": [
            "Autoatendimento com onboarding assistido",
            "Suporte por WhatsApp, o canal que o produtor já usa",
            "Relatório de intervenção periódico por talhão",
            "Pilotos com cooperativas e co-criação das regras",
        ],
    },
    "canais": {
        "titulo": "Canais",
        "itens": [
            "Cooperativas e revendas, que já visitam o produtor",
            "Dias de campo e demonstrações",
            "Painel web e alertas por mensagem",
            "Agrônomos parceiros que indicam e acompanham",
        ],
    },
    "segmentos": {
        "titulo": "Segmentos de clientes",
        "itens": [
            "Pequenos e médios produtores de hortifrúti, a começar pelo tomate (H)",
            "Cooperativas, que contratam para os cooperados",
            "Consultorias e agrônomos de campo, como usuários multiplicadores",
            "Depois: indústria de processamento e revendas",
        ],
    },
    "custos": {
        "titulo": "Estrutura de custos",
        "itens": [
            "Fixos: equipe, manutenção e retreino do modelo, segurança",
            "Variáveis: nuvem e broker, que crescem com eventos e área monitorada",
            "Sensores e câmeras, em comodato ou vendidos com margem",
            "Suporte e onboarding; comissão dos parceiros de venda",
        ],
    },
    "receitas": {
        "titulo": "Fontes de receita",
        "itens": [
            "Assinatura mensal por área monitorada (H)",
            "Licença para cooperativa, por cooperado atendido (H)",
            "Kit de sensores e instalação (H)",
            "Integração por API e relatórios sob medida",
        ],
    },
}

PROPOSTA_DE_VALOR = {
    "Tarefas do cliente": [
        "Inspecionar a lavoura e achar folhas com doença",
        "Decidir onde aplicar defensivo e onde irrigar",
        "Registrar o que aconteceu em cada talhão",
    ],
    "Dores": [
        "A inspeção a pé é lenta e depende do olho de quem vê",
        "A doença é percebida tarde, quando já se espalhou",
        "Aplicar na fazenda inteira custa caro e desperdiça produto",
        "Sem histórico, não se sabe se o problema cresce ou recua",
    ],
    "Ganhos esperados": [
        "Reduzir perdas de produtividade por doença",
        "Gastar menos com defensivo e com água",
        "Provar ao comprador e ao técnico o que foi feito",
    ],
    "Produtos e serviços": [
        "Classificação de folhas por foto, com confiança",
        "Painel por talhão e evolução por dia",
        "Alertas em tempo real de doença e de umidade crítica",
        "Relatório de intervenção com a ação recomendada",
    ],
    "Aliviadores de dores": [
        "Resultado em segundos, com o mesmo critério para todas as fotos",
        "Regra de persistência avisa antes de a doença se espalhar",
        "Alerta por talhão, não por fazenda",
        "Histórico guardado com data e talhão",
    ],
    "Geradores de ganho": [
        "Prioridade máxima (R5) quando doença alta e persistente coincidem",
        "Irrigação orientada pelo sensor de solo (S1)",
        "Exportação em CSV e JSON para o agrônomo e o comprador",
    ],
}

# Hipotese, como validar e indicador de sucesso
HIPOTESES = [
    (
        "O produtor sente que perde dinheiro por descobrir a doença tarde",
        "Entrevistar produtores de tomate e perguntar quanto perderam na última safra",
        "Parte dos entrevistados que relata perda por detecção tardia",
    ),
    (
        "O modelo acerta em folhas fotografadas no campo, não só no conjunto de testes",
        "Piloto em um talhão, comparando o resultado com a avaliação de um agrônomo",
        "Concordância com o agrônomo; hoje há 95% no conjunto de teste, em ambiente controlado",
    ),
    (
        "Aplicar só no talhão necessário reduz o gasto com defensivo",
        "Comparar duas áreas na mesma safra, com e sem as recomendações",
        "Litros de produto e custo por hectare",
    ),
    (
        "O produtor paga por área monitorada",
        "Testar três faixas de preço em conversas e no piloto",
        "Parte dos pilotos que aceita converter em assinatura, e a que preço",
    ),
    (
        "Cooperativas e revendas aceitam distribuir a solução",
        "Propor o piloto a duas cooperativas",
        "Cooperativas que assinam o piloto e quantos cooperados aderem",
    ),
]

CONCORRENCIA = [
    "Inspeção manual pelo agrônomo, que é o substituto de hoje e é o que mais pesa",
    "Aplicativos genéricos de diagnóstico por foto, sem a visão por talhão",
    "Plataformas de agricultura de precisão de grandes fabricantes, mais caras e fechadas",
    "Imagens de satélite e drone, que cobrem área mas não dão o diagnóstico da folha",
]
