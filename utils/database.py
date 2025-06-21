import sys
import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, Column, MetaData, String, Float, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import geopandas as gpd

# Adicionar o diretório pai ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.overpass import get_regiao_administrativa
from scripts.regioes_coordenadas import get_ra_por_coordenada


load_dotenv()

db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@" \
         f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"


engine = create_engine(db_url)


metadata = MetaData()

urban_images = Table(
    "urban_images", metadata,
    Column("place_id", PG_UUID(as_uuid=True), primary_key=True),
    Column("place_name", String),
    Column("latitude", Float),
    Column("longitude", Float)
)

def criar_tabela():
    metadata.create_all(engine)

def salvar_registro(place_id: uuid.UUID, place_name: str, lat: float, lon: float):
    with engine.begin() as conn:
        conn.execute(
            urban_images.insert().values(
                place_id=place_id,
                place_name=place_name,
                latitude=lat,
                longitude=lon
            )
        )

def obter_todos_registros(eg):
    """
    Faz o select inteiro da tabela urban_images.
    
    Returns:
        list: Lista de dicionários com todos os registros da tabela
    """
    with eg.begin() as conn:
        result = conn.execute(select(urban_images))
        registros = []
        
        for row in result:
            registros.append({
                'place_id': row.place_id,
                'place_name': row.place_name,
                'latitude': row.latitude,
                'longitude': row.longitude
            })
        
        return registros

def criar_tabela_com_regioes(eg, caminho_geojson: str = 'coordenadas_poligonais/regioes_df.geojson'):
    """
    Cria uma nova tabela 'urban_images_regioes' com a coluna place_name 
    renomeada baseada na função get_regiao_administrativa.
    
    Pega os dados da tabela original, descobre a região administrativa
    baseada na latitude e longitude, e insere na nova tabela.
    """
    # Definir a nova tabela
    urban_images_regioes = Table(
        "urban_images_reclassificada", metadata,
        Column("place_id", PG_UUID(as_uuid=True), primary_key=True),
        Column("regiao_administrativa", String),
        Column("latitude", Float),
        Column("longitude", Float)
    )
    
    # Criar a nova tabela se não existir
    urban_images_regioes.create(eg, checkfirst=True)
    
    # Obter todos os registros da tabela original
    registros_originais = obter_todos_registros(eg)
    
    print(f"Processando {len(registros_originais)} registros...")

    gdf_regioes = gpd.read_file(caminho_geojson)

    
    # Preparar dados em lote
    dados_lote = []
    for i, registro in enumerate(registros_originais):
        print(f"Processando registro {i+1}/{len(registros_originais)}...")
        
        # Descobrir a região administrativa baseada nas coordenadas
        regiao = get_ra_por_coordenada(
            registro['latitude'], 
            registro['longitude'],
            gdf_regioes,
            'name'
        )

        print(f"Registro {i+1}: {registro['place_id']} - Região: {regiao}")
        
        dados_lote.append({
            'place_id': registro['place_id'],
            'regiao_administrativa': regiao,
            'latitude': registro['latitude'],
            'longitude': registro['longitude']
        })
    
    # Inserir todos os dados em batch
    with eg.begin() as conn:
        conn.execute(urban_images_regioes.insert(), dados_lote)
    
    print("Tabela 'urban_images_regioes' criada e populada com sucesso!")
    
    return urban_images_regioes

