# Dockerfile para rodar aplicação Streamlit na porta 8501
FROM python:3.12-slim

WORKDIR /app

# copia e instala dependências
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia toda a estrutura do projeto
COPY . .

# expõe a porta que o Streamlit usa
EXPOSE 8501

# define o Python path para incluir o diretório raiz
ENV PYTHONPATH=/app

# usa exec form para que o Streamlit receba sinais diretos
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]

