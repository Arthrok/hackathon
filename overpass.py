# overpass.py
import requests
import random

def get_coordenadas():
    overpass_url = "https://overpass-api.de/api/interpreter"

    query = """
    [out:json][timeout:120];
    area["name"="Distrito Federal"][admin_level=4]->.df;

    (
      area["name"="Brasília"](area.df);
      area["name"="Gama"](area.df);
      area["name"="Taguatinga"](area.df);
      area["name"="Ceilândia"](area.df);
      area["name"="Samambaia"](area.df);
      area["name"="Planaltina"](area.df);
      area["name"="Paranoá"](area.df);
      area["name"="Núcleo Bandeirante"](area.df);
      area["name"="Sobradinho"](area.df);
      area["name"="Sobradinho II"](area.df);
      area["name"="Recanto das Emas"](area.df);
      area["name"="Riacho Fundo"](area.df);
      area["name"="Riacho Fundo II"](area.df);
      area["name"="Lago Norte"](area.df);
      area["name"="Lago Sul"](area.df);
      area["name"="Candangolândia"](area.df);
      area["name"="Santa Maria"](area.df);
      area["name"="São Sebastião"](area.df);
      area["name"="Cruzeiro"](area.df);
      area["name"="Sudoeste/Octogonal"](area.df);
      area["name"="Varjão"](area.df);
      area["name"="Park Way"](area.df);
      area["name"="SCIA"](area.df);
      area["name"="SIA"](area.df);
      area["name"="Vicente Pires"](area.df);
      area["name"="Fercal"](area.df);
    )->.searchAreas;

    (
      node["shop"](area.searchAreas);
      node["amenity"="pharmacy"](area.searchAreas);
      node["amenity"="bar"](area.searchAreas);
      node["amenity"="cafe"](area.searchAreas);
      node["amenity"="bus_station"](area.searchAreas);
      node["highway"="bus_stop"](area.searchAreas);
    );
    out center;
    """

    response = requests.post(overpass_url, data={"data": query})
    data = response.json()

    coordenadas = []
    for element in data["elements"]:
        if "lat" in element and "lon" in element:
            coordenadas.append((element["lat"], element["lon"]))

    return random.sample(coordenadas, min(20, len(coordenadas)))

def get_regiao_administrativa(lat, lon):
    """
    Determina a região administrativa com base nas coordenadas fornecidas.
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
    
    Returns:
        str: Nome da região administrativa ou "Região não identificada"
    """
    overpass_url = "https://overpass-api.de/api/interpreter"
    
    query = f"""
    [out:json][timeout:30];
    (
      is_in({lat}, {lon});
      area._["name"]["admin_level"];
    );
    out tags;
    """
    
    try:
        response = requests.post(overpass_url, data={"data": query})
        data = response.json()
        
        # Lista das regiões administrativas do DF
        regioes_df = [
            "Brasília", "Gama", "Taguatinga", "Ceilândia", "Samambaia",
            "Planaltina", "Paranoá", "Núcleo Bandeirante", "Sobradinho",
            "Sobradinho II", "Recanto das Emas", "Riacho Fundo",
            "Riacho Fundo II", "Lago Norte", "Lago Sul", "Candangolândia",
            "Santa Maria", "São Sebastião", "Cruzeiro", "Sudoeste/Octogonal",
            "Varjão", "Park Way", "SCIA", "SIA", "Vicente Pires", "Fercal"
        ]
        
        # Procura pela região administrativa nas tags retornadas
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name", "")
            
            # Verifica se o nome corresponde a uma região administrativa do DF
            if name in regioes_df:
                return name
                
            # Verifica correspondências parciais (para casos como "Sudoeste/Octogonal")
            for regiao in regioes_df:
                if regiao.lower() in name.lower() or name.lower() in regiao.lower():
                    return regiao
        
        return "Região não identificada"
        
    except Exception as e:
        print(f"Erro ao consultar região administrativa: {e}")
        return "Erro na consulta"

