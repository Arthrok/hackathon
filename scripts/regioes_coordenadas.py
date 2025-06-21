import geopandas as gpd
from shapely.geometry import Point

# Função para obter regiões administrativas com polígonos válidos a partir de um arquivo GeoJSON
def get_regioes_com_poligono(caminho_geojson):
    """
    Retorna uma lista de nomes das regiões administrativas com geometria válida.

    Args:
        caminho_geojson (str): Caminho para o arquivo GeoJSON.

    Returns:
        list: Lista de nomes das regiões com polígonos definidos.
    """
    # Lê o arquivo GeoJSON
    gdf = gpd.read_file(caminho_geojson)

    # Remove regiões com geometria nula ou inválida
    gdf_validas = gdf[gdf['geometry'].notnull() & gdf['geometry'].is_valid]

    # Extrai os nomes das regiões
    lista_regioes = gdf_validas['ra'].tolist()

    return lista_regioes

# print(get_regioes_com_poligono('regioes_ra_df.geojson'))




def get_ra_por_coordenada(lat: float, lon: float, gdf_regioes, ra_ou_name) -> str | None:
    """
    Retorna o nome da Região Administrativa (RA) para as coordenadas fornecidas.

    Args:
        lat (float): Latitude do ponto.
        lon (float): Longitude do ponto.
        caminho_geojson (str): Caminho para o arquivo GeoJSON com polígonos das RAs.

    Returns:
        str | None: Nome da RA encontrada, ou None se nenhuma for encontrada.
    """
    # 1. Carrega as regiões administrativas
    # gdf_regioes = gpd.read_file(caminho_geojson)

    # 2. Cria um GeoDataFrame para o ponto
    gdf_ponto = gpd.GeoDataFrame(
        [{'geometry': Point(lon, lat)}],
        crs="EPSG:4326"
    )

    # 3. Spatial join — vértice dentro do polígono
    joined = gdf_ponto.sjoin(gdf_regioes[[ra_ou_name, 'geometry']],
                             how="left", predicate="within")

    # 4. Extrai o nome da RA, se existir
    return joined.iloc[0][ra_ou_name] if ra_ou_name in joined.columns else None

