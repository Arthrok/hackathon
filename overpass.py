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
