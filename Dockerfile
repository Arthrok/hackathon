# Dockerfile simples para rodar streamlit_app.py na porta 8501
FROM python:3.12-slim

WORKDIR /app

# copia e instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copia o app
COPY streamlit_app.py .

# expõe a porta que o Streamlit usa
EXPOSE 8501

# usa exec form para que o Streamlit receba sinais diretos
CMD ["streamlit", "run", "streamlit_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]

