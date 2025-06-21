# Criminologia Ambiental

Projeto para coletar imagens urbanas de locais movimentados no Distrito Federal utilizando a API do Mapillary, armazenando-as no MinIO, registrando metadados no PostgreSQL e classificando as imagens com base na percepção urbana.

🔗 **Visualização Interativa**: [criminologia-ambiental.arthrok.shop](https://criminologia-ambiental.arthrok.shop/)

---

## Requisitos

* Docker + Docker Compose
* Python 3.10+
* Conta na [Mapillary](https://www.mapillary.com/) para obter o token de acesso

---

## Instalação

### 1. Clone o repositório

```bash
git clone https://github.com/Arthrok/hackathon.git
cd hackathon
```

### 2. Crie o ambiente virtual

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

### 4. Crie o arquivo `.env`

Crie um arquivo `.env` na raiz com o seguinte conteúdo:

```bash
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

* MinIO Console: [http://localhost:9001](http://localhost:9001)
* PostgreSQL: acessível na porta `5432` com os dados do `.env`

---

## 🚀 Fluxo de Execução

Execute os scripts na ordem abaixo:

### 1. Extração de coordenadas e imagens

```bash
python map.py
```

O script irá:

* Buscar coordenadas urbanas via Overpass
* Baixar imagens da região com a API do Mapillary
* Salvar as imagens no MinIO
* Armazenar metadados no PostgreSQL (tabela `urban_images`)

### 2. Classificação das imagens

```bash
python eval.py
```

Esse script realiza a classificação das imagens usando o modelo Place Pulse, gerando scores para os atributos urbanos:

* Segurança (`safety`)
* Dinamicidade (`lively`)
* Riqueza (`wealthy`)

Os scores são salvos na tabela `score` no PostgreSQL, associados ao `place_id` das imagens.

### 3. Cálculo do Score Final e Heatmaps

```bash
python calculate_safety_score.py
```

Este script gera scores agregados e visualizações como heatmaps, atualizando e consolidando os dados para visualização.

---

## 📊 Visualização com Streamlit

Utilizamos uma aplicação **Streamlit** para exibir os resultados de forma interativa:

```bash
streamlit run streamlit_app.py
```

---

## 📁 Estrutura

```bash
.
├── human-perception-place-pulse/   # Modelo Place Pulse para classificação
├── coordenadas_poligonais/
├── .env
├── .gitignore
├── Dockerfile                      # Dockerização da aplicação Streamlit
├── README.md
├── calculate_safety_score.py       # Script para gerar scores e heatmaps
├── database.py
├── docker-compose.yaml
├── map.py                          # Script de extração inicial de imagens e coordenadas
├── overpass.py                     # Integração com Overpass API
├── requirements.txt
├── storage.py
└── streamlit_app.py                # Aplicação Streamlit para visualização
```

---

## Resultado Esperado

* Imagens armazenadas no bucket `images` do MinIO
* Metadados salvos na tabela `urban_images`
* Scores de percepção urbana salvos na tabela `score`
* Interface interativa em Streamlit exibindo os resultados
