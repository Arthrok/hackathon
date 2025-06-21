# Criminologia Ambiental

Projeto para coletar imagens urbanas de locais movimentados no Distrito Federal utilizando a API do Mapillary, armazenando-as no MinIO, registrando metadados no PostgreSQL e classificando as imagens com base na percepção urbana.

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

## Executando o script principal

```bash
python3 app/map.py
```

O script irá:

1. Buscar coordenadas urbanas via Overpass
2. Baixar imagens da região com a API do Mapillary
3. Salvar as imagens no MinIO
4. Armazenar os metadados no PostgreSQL (tabela `urban_images`)

### Executando scripts de processamento

Para calcular os scores de segurança:
```bash
python3 scripts/calculate_safety_score.py
```

Para reclassificar regiões:
```bash
python3 scripts/reclassificacao.py
```

---

## Classificação das Imagens com Place Pulse

Após a extração das imagens, realizamos a **classificação de percepção urbana** utilizando o repositório:

🔗 [strawmelon11/human-perception-place-pulse](https://github.com/strawmelon11/human-perception-place-pulse)

Este repositório implementa modelos treinados com a base de dados **Place Pulse 2.0**, permitindo avaliar atributos como:

* Segurança (`safety`)
* Dinamicidade (`lively`)
* Riqueza (`wealthy`)

### Fluxo de Classificação

1. Extração das imagens (via Mapillary)
2. Classificação com o modelo Place Pulse
3. Geração dos scores
4. Atualização dos scores na tabela `score` no PostgreSQL
5. Visualização dos resultados na interface Streamlit

A classificação é feita localmente. Os scores são vinculados ao `place_id` de cada imagem.

---

## 📊 Visualização com Streamlit

Utilizamos uma aplicação em **Streamlit** para exibir os scores em um mapa interativo.

```bash
streamlit run app/streamlit_app.py
```

Ou alternativamente, você pode executar usando python3:
```bash
python3 -m streamlit run app/streamlit_app.py
```

---

## 📁 Estrutura

```bash
.
├── app/                             # Código relacionado ao Streamlit
│   ├── streamlit_app.py
│   ├── map.py
│   └── requirements.txt
│
├── model/                           # Modelo Place Pulse para classificação
│   └── human-perception-place-pulse/
│
├── scripts/                         # Scripts de processamento
│   ├── calculate_safety_score.py
│   ├── overpass.py
│   ├── reclassificacao.py
│   └── regioes_coordenadas.py
│
├── utils/                           # Utilitários gerais e auxiliares
│   ├── database.py
│   └── storage.py
│
├── docker/
│   ├── Dockerfile                   # Dockerização da aplicação Streamlit
│   └── docker-compose.yaml
│
├── coordenadas_poligonais/
│   ├── construcao_base_geojson.py
│   ├── regioes_df.geojson
│   └── regioes_ra_df.geojson
│
├── .env.example
├── .gitignore
├── docker-compose.yaml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## Resultado Esperado

* Imagens armazenadas no bucket `images` do MinIO
* Metadados salvos na tabela `urban_images`
* Scores de percepção urbana salvos na tabela `score`
* Interface interativa em Streamlit exibindo os resultados
