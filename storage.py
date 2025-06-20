import os
from dotenv import load_dotenv
from minio import Minio

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET_NAME = os.getenv("MINIO_BUCKET")

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
)

def upload_imagem(local_path: str, object_name: str):
    minio_client.fput_object(
        BUCKET_NAME,
        object_name,
        local_path,
        content_type="image/jpeg"
    )
    os.remove(local_path)
