import requests
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
import time

def fetch_region_poly(region_name):
    print(f"  📡 Consultando {region_name}")
    
    # Consulta melhorada para capturar relation boundaries
    query = f"""
    [out:json][timeout:60];
    area["name"="Distrito Federal"][admin_level=4]->.df;
    rel["boundary"="administrative"]["admin_level"="8"]["name"="{region_name}"](area.df);
    out geom;
    """
    
    resp = requests.post("https://overpass-api.de/api/interpreter", data={"data": query})
    if resp.status_code != 200:
        print(f"  ❌ Erro na API: {resp.status_code}")
        return None
        
    data = resp.json()
    
    if not data.get("elements"):
        print(f"  ⚠️ Nenhum elemento encontrado")
        return None
    
    print(f"  ✅ Encontrados {len(data['elements'])} elementos")
    
    # Processa relations
    for elem in data["elements"]:
        if elem["type"] == "relation" and "members" in elem:
            # Coleta ways do boundary exterior
            outer_ways = [m["ref"] for m in elem["members"] if m["role"] == "outer" and m["type"] == "way"]
            
            if outer_ways:
                # Consulta geometrias dos ways
                way_ids = ",".join(map(str, outer_ways))
                geom_query = f"""
                [out:json][timeout:60];
                way(id:{way_ids});
                out geom;
                """
                
                geom_resp = requests.post("https://overpass-api.de/api/interpreter", data={"data": geom_query})
                if geom_resp.status_code == 200:
                    geom_data = geom_resp.json()
                    
                    # Coleta todos os ways com suas coordenadas
                    ways_data = {}
                    for way in geom_data.get("elements", []):
                        if "geometry" in way:
                            coords = [(pt["lon"], pt["lat"]) for pt in way["geometry"]]
                            ways_data[way["id"]] = coords
                    
                    # Tenta conectar os ways em ordem
                    if ways_data:
                        try:
                            # Começa com o primeiro way
                            first_way_id = list(ways_data.keys())[0]
                            connected_coords = ways_data[first_way_id][:]
                            used_ways = {first_way_id}
                            
                            # Tenta conectar os outros ways
                            while len(used_ways) < len(ways_data):
                                last_point = connected_coords[-1]
                                found_connection = False
                                
                                for way_id, coords in ways_data.items():
                                    if way_id in used_ways:
                                        continue
                                    
                                    # Verifica se este way conecta ao final da linha atual
                                    if coords[0] == last_point:
                                        connected_coords.extend(coords[1:])  # Remove primeiro ponto (duplicado)
                                        used_ways.add(way_id)
                                        found_connection = True
                                        break
                                    elif coords[-1] == last_point:
                                        # Way está na direção oposta
                                        connected_coords.extend(reversed(coords[:-1]))  # Remove último ponto e inverte
                                        used_ways.add(way_id)
                                        found_connection = True
                                        break
                                
                                if not found_connection:
                                    # Se não conseguiu conectar, tenta uma abordagem mais simples
                                    print(f"  ⚠️ Não conseguiu conectar todos os ways, usando abordagem simples")
                                    all_coords = []
                                    for coords in ways_data.values():
                                        all_coords.extend(coords[:-1])  # Remove último ponto para evitar duplicação
                                    
                                    if all_coords and len(all_coords) >= 3:
                                        all_coords.append(all_coords[0])  # Fecha o polígono
                                        poly = Polygon(all_coords)
                                        if poly.is_valid and poly.area > 0:
                                            print(f"  🎯 Polígono criado (método simples)!")
                                            return poly
                                    break
                            
                            # Fecha o polígono se necessário
                            if connected_coords and connected_coords[0] != connected_coords[-1]:
                                connected_coords.append(connected_coords[0])
                            
                            if len(connected_coords) >= 4:
                                poly = Polygon(connected_coords)
                                if poly.is_valid and poly.area > 0:
                                    print(f"  🎯 Polígono criado (método conectado)!")
                                    return poly
                                else:
                                    print(f"  ⚠️ Polígono inválido ou sem área")
                        
                        except Exception as e:
                            print(f"  ⚠️ Erro ao conectar ways: {e}")
    
    # Fallback para ways diretos
    polys = []
    for elem in data["elements"]:
        if elem["type"] == "way" and "geometry" in elem:
            coords = [(pt["lon"], pt["lat"]) for pt in elem["geometry"]]
            if len(coords) >= 4:
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                try:
                    poly = Polygon(coords)
                    if poly.is_valid and poly.area > 0:
                        polys.append(poly)
                except Exception as e:
                    print(f"  ⚠️ Erro: {e}")
    
    if not polys:
        print(f"  ❌ Nenhum polígono válido")
        return None
    elif len(polys) == 1:
        return polys[0]
    else:
        return MultiPolygon(polys)

def build_df(regions):
    records = []
    for name in regions:
        print("🔍 Buscando", name)
        geom = fetch_region_poly(name)
        records.append({"name": name, "geometry": geom})
        time.sleep(0.5)  # Pausa para não sobrecarregar a API
    return gpd.GeoDataFrame(records, crs="EPSG:4326")

regions = ["Brasília","Gama","Taguatinga","Ceilândia","Samambaia",
            "Planaltina","Paranoá","Núcleo Bandeirante","Sobradinho",
            "Sobradinho II","Recanto das Emas","Riacho Fundo",
            "Riacho Fundo II","Lago Norte","Lago Sul","Candangolândia",
            "Santa Maria","São Sebastião","Cruzeiro","Sudoeste/Octogonal",
            "Varjão","Park Way","SCIA","SIA","Vicente Pires"]

gdf = build_df(regions)
gdf.to_file("coordenadas_poligonais/regioes_df.geojson", driver="GeoJSON")

