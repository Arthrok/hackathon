# coding=UTF-8
import os
import pandas as pd
import torch
import torch.nn as nn
from torchvision import transforms as T
from PIL import Image
from transformers import AutoModel
from huggingface_hub import snapshot_download
from Model_01 import Net  # Add this import
from minio import Minio
from dotenv import load_dotenv
import io
from sqlalchemy import create_engine, Table, Column, MetaData, String, Float
from sqlalchemy.dialects.postgresql import insert

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Load environment variables from parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# MinIO configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET_NAME = os.getenv("MINIO_BUCKET")

print(f"MINIO_ENDPOINT: {MINIO_ENDPOINT}")
print(f"MINIO_ACCESS_KEY: {MINIO_ACCESS_KEY}")
print(f"MINIO_SECRET_KEY: {MINIO_SECRET_KEY}")
print(f"BUCKET_NAME: {BUCKET_NAME}")

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

# PostgreSQL configuration
print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST')}")
print(f"POSTGRES_PORT: {os.getenv('POSTGRES_PORT')}")
print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER')}")
print(f"POSTGRES_DB: {os.getenv('POSTGRES_DB')}")

db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@" \
         f"{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

print(f"Database URL: {db_url}")
engine = create_engine(db_url)
metadata = MetaData()

# Define classification table
classification_table = Table(
    "classification", metadata,
    Column("img_path", String, primary_key=True),
    Column("safety", Float),
    Column("lively", Float),
    Column("wealthy", Float),
    Column("beautiful", Float),
    Column("boring", Float),
    Column("depressing", Float),
    schema="public"
)

perception = ['safety', 'lively', 'wealthy',
              'beautiful', 'boring', 'depressing']
model_dict = {
    'safety': 'safety.pth',
    'lively': 'lively.pth',
    'wealthy': 'wealthy.pth',
    'beautiful': 'beautiful.pth',
    'boring': 'boring.pth',
    'depressing': 'depressing.pth',
}


train_transform = T.Compose([
    T.Resize((384, 384)),
    T.ToTensor(),
    T.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225])
])


def predict(model, img_data, device):
    """
    Predict using model with image data from memory
    img_data: bytes or PIL Image object
    """
    if isinstance(img_data, bytes):
        img = Image.open(io.BytesIO(img_data))
    else:
        img = img_data
    
    if img.mode != "RGB":
        img = img.convert("RGB")
    img = train_transform(img)
    img = img.view(1, 3, 384, 384)
    # inference
    if device == 'cuda:0':
        pred = model(img.cuda())
    else:
        pred = model(img)
    softmax = nn.Softmax(dim=1)
    pred = softmax(pred)[0][1].item()
    pred = round(pred*10, 2)

    return pred


def get_object_tags(object_name):
    """
    Get tags of an object from MinIO
    Returns dict of tags or empty dict if no tags
    """
    try:
        # Try to get object tags - MinIO may not support this fully
        tags_response = minio_client.get_object_tags(BUCKET_NAME, object_name)
        return tags_response
    except Exception as e:
        # MinIO may not support tags like AWS S3, return empty dict
        return {}


def set_object_tag(object_name, key, value):
    """
    Set a tag on an object in MinIO
    """
    try:
        # Get existing tags
        existing_tags = get_object_tags(object_name)
        
        # Add new tag
        existing_tags[key] = value
        
        # Set updated tags
        minio_client.set_object_tags(BUCKET_NAME, object_name, existing_tags)
        return True
    except Exception as e:
        print(f"⚠️ Tags não suportadas no MinIO, usando abordagem alternativa")
        return False


def is_image_processed(object_name):
    """
    Check if image was already processed by looking for a corresponding marker file
    """
    try:
        marker_name = f"processed/{object_name}.done"
        minio_client.stat_object(BUCKET_NAME, marker_name)
        return True
    except Exception:
        return False


def mark_image_as_processed(object_name):
    """
    Mark image as processed by creating a marker file
    """
    try:
        marker_name = f"processed/{object_name}.done"
        marker_content = f"Processed on {pd.Timestamp.now()}"
        minio_client.put_object(
            BUCKET_NAME, 
            marker_name, 
            io.BytesIO(marker_content.encode('utf-8')), 
            len(marker_content.encode('utf-8'))
        )
        return True
    except Exception as e:
        print(f"Erro ao criar marcador para {object_name}: {e}")
        return False


def get_images_from_minio():
    """
    Get list of images from MinIO bucket that are not marked as processed
    Returns list of object names
    """
    try:
        objects = minio_client.list_objects(BUCKET_NAME, recursive=True)
        image_names = []
        processed_count = 0
        
        for obj in objects:
            # Skip marker files
            if obj.object_name.startswith('processed/'):
                continue
                
            if obj.object_name.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Check if image is already processed
                if is_image_processed(obj.object_name):
                    processed_count += 1
                    print(f"⏭️ Pulando {obj.object_name} (já processada)")
                    continue
                
                image_names.append(obj.object_name)
        
        print(f"📊 Total de imagens no bucket: {len(image_names) + processed_count}")
        print(f"✅ Já processadas: {processed_count}")
        print(f"⏳ Para processar: {len(image_names)}")
        
        return image_names
    except Exception as e:
        print(f"Erro ao listar objetos do MinIO: {e}")
        return []


def download_image_from_minio(object_name):
    """
    Download image from MinIO bucket and return as bytes
    """
    try:
        response = minio_client.get_object(BUCKET_NAME, object_name)
        image_data = response.read()
        response.close()
        response.release_conn()
        return image_data
    except Exception as e:
        print(f"Erro ao baixar imagem {object_name}: {e}")
        return None


def save_classification_to_db(image_scores):
    """
    Save classification scores to PostgreSQL database
    """
    try:
        with engine.begin() as conn:
            # Use upsert (INSERT ... ON CONFLICT DO UPDATE)
            stmt = insert(classification_table).values(**image_scores)
            stmt = stmt.on_conflict_do_update(
                index_elements=['img_path'],
                set_={
                    'safety': stmt.excluded.safety,
                    'lively': stmt.excluded.lively,
                    'wealthy': stmt.excluded.wealthy,
                    'beautiful': stmt.excluded.beautiful,
                    'boring': stmt.excluded.boring,
                    'depressing': stmt.excluded.depressing,
                }
            )
            conn.execute(stmt)
        print(f"  ✅ Dados salvos no banco para {image_scores['img_path']}")
        return True
    except Exception as e:
        print(f"  ❌ Erro ao salvar no banco: {e}")
        return False


if __name__ == "__main__":
    
    model_load_path = "./model"   # model dir path
    out_Path = "./output"     # output path
    
    # download model
    print("Downloading models ...")
    snapshot_download(repo_id="Jiani11/human-perception-place-pulse",
                      allow_patterns=["*.pth", "README.md"], local_dir=model_load_path)

    # Get images from MinIO
    print("Conectando ao MinIO e listando imagens...")
    image_names = get_images_from_minio()
    
    if not image_names:
        print("❌ Nenhuma imagem encontrada no bucket MinIO!")
        exit(1)
    
    print(f"📸 Encontradas {len(image_names)} imagens no bucket '{BUCKET_NAME}'")

    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    print("using device:{} ".format(device))
    
    # Check if the directory exists, if not, create it (for backup CSV)
    if not os.path.exists(out_Path):
        os.makedirs(out_Path)
    
    # Counters for tracking results
    total_processed = 0
    total_saved_db = 0
    
    # Create backup DataFrame for CSV
    classification_df = pd.DataFrame(columns=['img_path'] + perception)
    
    # Process each image and save directly to database
    for img_name in image_names:
        print(f"Processando imagem: {img_name}")
        
        # Download image from MinIO
        img_data = download_image_from_minio(img_name)
        
        if img_data is None:
            print(f"⚠️ Erro ao baixar {img_name}, pulando...")
            continue
        
        # Dictionary to store scores for this image
        image_scores = {'img_path': img_name}
        all_scores_valid = True
        
        # Process each perception dimension
        for p in perception:
            print(f"  Classificando para {p}...")
            
            # Load model for this perception
            model_path = model_load_path + "/" + model_dict[p]
            model = torch.load(model_path, map_location=torch.device(device), weights_only=False)
            if torch.cuda.device_count() > 1:
                model = nn.DataParallel(model)
            model = model.to(device)
            model.eval()
            
            try:
                score = predict(model, img_data, device)
                image_scores[p] = score
                print(f"    {p}: {score}")
            except Exception as e:
                print(f"    ❌ Erro ao processar {p}: {e}")
                image_scores[p] = None
                all_scores_valid = False
                continue
        
        # Only save to database if all scores are valid
        if all_scores_valid and None not in image_scores.values():
            if save_classification_to_db(image_scores):
                total_saved_db += 1
                # Mark image as processed in MinIO
                if mark_image_as_processed(img_name):
                    print(f"  🏷️ Imagem {img_name} marcada como processada")
                else:
                    print(f"  ⚠️ Erro ao marcar {img_name} como processada")
        else:
            print(f"  ⚠️ Alguns scores inválidos para {img_name}, não salvando no banco")
        
        # Add to backup DataFrame regardless
        new_row = pd.DataFrame([image_scores])
        classification_df = pd.concat([classification_df, new_row], ignore_index=True)
        
        total_processed += 1
        print(f"✅ {img_name} processada ({total_processed}/{len(image_names)})!")
    
    print(f"\n🎉 Processamento completo!")
    print(f"📊 Total de imagens processadas: {total_processed}")
    print(f"💾 Total salvo no banco PostgreSQL: {total_saved_db}")
    print(f"🗂️ Tabela do banco: public.classification")
