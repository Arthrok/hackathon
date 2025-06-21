import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, Table, Column, MetaData, String, Float, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from regioes_coordenadas import get_ra_por_coordenada
import geopandas as gpd

# Importar as funções necessárias do database.py
from database import obter_todos_registros, criar_tabela_com_regioes

# Carregar variáveis de ambiente
load_dotenv()

# Configurar conexão com o banco
db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@" \
         f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

engine = create_engine(db_url)

# Definir metadata
metadata = MetaData()

# Função principal para executar a reclassificação
def executar_reclassificacao():
    """
    Executa a função criar_tabela_com_regioes usando o engine configurado.
    """
    try:
        print("Iniciando processo de reclassificação...")
        
        # Executar a função de reclassificação
        tabela_criada = criar_tabela_com_regioes(
            eg=engine,
            caminho_geojson='coordenadas_poligonais/regioes_df.geojson'
        )
        
        print("Reclassificação concluída com sucesso!")
        return tabela_criada
        
    except Exception as e:
        print(f"Erro durante a reclassificação: {e}")
        raise e

if __name__ == "__main__":
    # Executar a reclassificação quando o script for executado diretamente
    executar_reclassificacao()



