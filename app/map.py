import sys
import os
import uuid
import time
import requests
from dotenv import load_dotenv

# Adicionar o diretório pai ao path para importar os módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.overpass import get_coordenadas
from utils.storage import upload_imagem
from utils.database import criar_tabela, salvar_registro

load_dotenv()
access_token = os.getenv("MAPILLARY_ACCESS_TOKEN")

criar_tabela()
coordenadas = get_coordenadas()

def inferir_regiao(lat, lon):
    if lat < -15.78 and lon < -47.9:
        return "Ceilândia"
    elif lat < -15.75 and lon < -48:
        return "Samambaia"
    elif lat > -15.7:
        return "Plano Piloto"
    else:
        return "Taguatinga"

for i, (lat, lon) in enumerate(coordenadas[:20]):
    bbox = f"{lon - 0.001},{lat - 0.001},{lon + 0.001},{lat + 0.001}"
    url = "https://graph.mapillary.com/images"
    params = {
        "fields": "id,thumb_2048_url",
        "bbox": bbox,
        "limit": 1,
        "access_token": access_token
    }

    try:
        r = requests.get(url, params=params)
        data = r.json()
        if data.get("data"):
            img = data["data"][0]
            img_url = img["thumb_2048_url"]
            img_data = requests.get(img_url).content

            place_id = uuid.uuid4()
            image_name = f"{place_id}.jpg"
            temp_path = f"/tmp/{image_name}"

            with open(temp_path, "wb") as f:
                f.write(img_data)

            upload_imagem(temp_path, image_name)
            salvar_registro(place_id, inferir_regiao(lat, lon), lat, lon)

            print(f"✅ {image_name} salva no MinIO e registrada no banco.")
            time.sleep(1)
        else:
            print(f"⚠️ Nenhuma imagem para {lat}, {lon}")
    except Exception as e:
        print(f"❌ Erro em {lat}, {lon}: {e}")
