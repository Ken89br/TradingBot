# data/google_drive_client.py
import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import io
import logging

logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
GOOGLE_CREDENTIALS_ENV = "GOOGLE_CREDENTIALS_JSON"
DEFAULT_SHARE_EMAIL = "kendeabreu24@gmail.com"

# IDs das pastas no seu Google Drive
CSV_FOLDER_ID = "1-2NSyy8C4kuBt_Rb6KKB42CVOxJLzTq8"
PKL_FOLDER_ID = "1-9FzKbCYdYuS2peZ5WlCTdtR7ayJZPH9"

def get_drive_service():
    creds = None
    # 1. Tenta arquivo físico (dev local)
    if os.path.isfile(SERVICE_ACCOUNT_FILE):
        creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    # 2. Tenta variável de ambiente (produção cloud)
    else:
        json_creds = os.environ.get(GOOGLE_CREDENTIALS_ENV)
        if not json_creds:
            raise RuntimeError("Credenciais do Google não encontradas! Configure o arquivo credentials.json ou a variável GOOGLE_CREDENTIALS_JSON.")
        creds_dict = json.loads(json_creds)
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def share_file_with_user(file_id, user_email=DEFAULT_SHARE_EMAIL):
    service = get_drive_service()
    permission = {
        'type': 'user',
        'role': 'writer',  # Pode ser 'reader' se quiser só leitura
        'emailAddress': user_email
    }
    try:
        service.permissions().create(fileId=file_id, body=permission, sendNotificationEmail=False).execute()
        print(f"✅ Arquivo compartilhado com {user_email} (ID: {file_id})")
    except Exception as e:
        print(f"⚠️ Falha ao compartilhar arquivo {file_id} com {user_email}: {e}")

def get_folder_id_for_file(filename):
    if filename.lower().endswith('.csv'):
        return CSV_FOLDER_ID
    elif filename.lower().endswith('.pkl'):
        return PKL_FOLDER_ID
    return None  # Ou pode definir uma pasta padrão se quiser

def upload_file(filepath, drive_folder_id=None, share_with_email=DEFAULT_SHARE_EMAIL):
    # Se não passar pasta explicitamente, decide automaticamente pela extensão
    if drive_folder_id is None:
        drive_folder_id = get_folder_id_for_file(filepath)
    service = get_drive_service()
    filename = os.path.basename(filepath)
    file_metadata = {'name': filename}
    if drive_folder_id:
        file_metadata['parents'] = [drive_folder_id]
    media = MediaFileUpload(filepath, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')
    print(f"✅ Upload concluído: {filename} (ID: {file_id})")
    if share_with_email:
        share_file_with_user(file_id, share_with_email)
    return file_id

def download_file(filename, destination_path, drive_folder_id=None, share_with_email=DEFAULT_SHARE_EMAIL):
    service = get_drive_service()
    file_id = find_file_id(filename, drive_folder_id)
    if not file_id:
        raise FileNotFoundError(f"Arquivo '{filename}' não encontrado no Google Drive.")
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(destination_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()
    print(f"✅ Download concluído: {filename} (ID: {file_id})")
    if share_with_email:
        share_file_with_user(file_id, share_with_email)

def find_file_id(filename, drive_folder_id=None):
    service = get_drive_service()
    query = f"name = '{filename}'"
    if drive_folder_id:
        query += f" and '{drive_folder_id}' in parents"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get('files', [])
    if files:
        return files[0]['id']
    return None
