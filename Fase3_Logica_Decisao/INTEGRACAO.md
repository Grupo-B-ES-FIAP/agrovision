# Guia de integração no projeto principal

1. Crie uma branch própria (ex.: `feature/fase3-logica-decisao`).
2. Copie `motor_decisao.py` para a **raiz** do AgroVision, ao lado de `app.py`.
3. Mantenha o CSV `dados/analises_tratadas.csv` da Fase 2. O motor espera colunas `data`, `localidade` e `categoria`, separadas por `;`; datas no formato `AAAA-MM-DD` e categorias `Doente` ou `Saudável`.
4. Rode `python teste_regras.py` e depois `python motor_decisao.py` na raiz do projeto. O segundo comando gera `dados/alertas.json`.
5. No `app.py` principal, integre a importação `from motor_decisao import executar as executar_decisoes` e chame `resultado = executar_decisoes()` depois da atualização do pipeline. Exiba `resultado["alertas"]` em uma aba ou seção do Streamlit.
6. **Não substitua o `app.py` dos colegas integralmente.** O ZIP completo da Fase 3, compartilhado separadamente, contém uma implementação de referência da aba `Inteligência no Campo`. Faça merge somente das partes relevantes.
7. Abra um Pull Request para revisão, indicando os testes e anexando o PDF no repositório.

## Contrato de saída

`executar()` retorna um dicionário com `gerado_em`, `fonte`, `criterios_experimentais` e `alertas`. Cada alerta contém `data`, `total`, `doentes`, `percentual_doentes`, `talhao`, `nivel`, `regra`, `persistencia_3_dias`, `controle_recomendado`, `situacao_normal` e `recomendacao`.

## Atenção

O CSV deve conter as datas e categorias adequadas. `executar()` grava `dados/alertas.json`; revise se esse arquivo gerado deve ser versionado ou ignorado no repositório principal. O módulo não identifica pragas específicas nem executa controles físicos.
