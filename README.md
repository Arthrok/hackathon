# 🏙️ Urban Image Collector

Projeto para coletar imagens urbanas de locais movimentados no Distrito Federal utilizando a API do Mapillary, armazenando-as no MinIO e registrando metadados no PostgreSQL.

## 🚀 Requisitos

- Docker + Docker Compose  
- Python 3.10+  
- Conta na [Mapillary](https://www.mapillary.com/) para obter o token de acesso

---

## ⚙️ Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/seu-repo.git
cd seu-repo
```

### 2. Crie o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\\Scripts\\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Crie o arquivo `.env`

Crie um arquivo `.env` na raiz com o seguinte conteúdo:

```
# Mapillary
MAPILLARY_ACCESS_TOKEN=MLY|...seu_token...

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=hackathon
POSTGRES_PASSWORD=hackathon
POSTGRES_DB=hackathon

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=images
```

---

## 🐳 Subindo os serviços

```bash
docker-compose up -d
```

- MinIO Console: http://localhost:9001  
- PostgreSQL: acessível na porta 5432 com os dados do `.env`

---

## 🏗️ Executando o script principal

```bash
python map.py
```

O script irá:

1. Buscar coordenadas urbanas via Overpass  
2. Baixar imagens da região com a API do Mapillary  
3. Salvar as imagens no MinIO  
4. Armazenar os metadados no PostgreSQL

---

## 📁 Estrutura

```
.
├── .env
├── docker-compose.yml
├── map.py
├── overpass.py
├── storage.py
├── database.py
├── requirements.txt
└── README.md
```

---

## ✅ Resultado

- Imagens armazenadas no bucket `images` no MinIO  
- Metadados registrados na tabela `urban_images` no PostgreSQL
