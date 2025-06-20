import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, Column, MetaData, String, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

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
