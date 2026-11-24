# Imagem unica: painel, produtor, consumidor e criacao dos topicos, cada um com seu comando
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias antes do codigo: mexer no codigo nao refaz esta camada
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pyproject.toml ./
COPY src ./src
COPY models ./models
COPY data/exemplos ./data/exemplos
COPY streaming/topicos.json ./streaming/topicos.json
# Editavel: o projeto acha data/ e models/ a partir de /app
RUN pip install --no-deps -e .

# Sem privilegios de root. A pasta de saida nasce aqui para o volume herdar o dono
RUN useradd --create-home agro && mkdir -p data/saida && chown -R agro:agro /app
USER agro

EXPOSE 8501

CMD ["streamlit", "run", "src/agrovision/app.py", \
     "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
