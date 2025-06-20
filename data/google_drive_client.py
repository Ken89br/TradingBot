#data/google_drive_client.py
import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import io

SCOPES = ['https://www.googleapis.com/auth/drive.file']
SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '..', 'credentials.json')
GOOGLE_CREDENTIALS_ENV = "GOOGLE_CREDENTIALS_JSON"

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

def upload_file(filepath, drive_folder_id=None):
    service = get_drive_service()
    filename = os.path.basename(filepath)
    file_metadata = {'name': filename}
    if drive_folder_id:
        file_metadata['parents'] = [drive_folder_id]
    media = MediaFileUpload(filepath, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return file.get('id')

def download_file(filename, destination_path, drive_folder_id=None):
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
