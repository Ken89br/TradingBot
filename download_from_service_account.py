from google.oauth2 import service_account
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseDownload
import os

# ==== CONFIGURE AQUI ====
SERVICE_ACCOUNT_FILE = 'credentials.json'
FOLDER_ID = '1-2NSyy8C4kuBt_Rb6KKB42CVOxJLzTq8'  # Substitua pelo ID da pasta no Drive
DEST_DIR = './downloads/csvdoservice'                 # Pasta local onde salvar os arquivos
# ========================

creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=['https://www.googleapis.com/auth/drive']
)
service = build('drive', 'v3', credentials=creds)

def list_files_in_folder(folder_id):
    files = []
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType, modifiedTime)',
            pageToken=page_token
        ).execute()
        files.extend(response.get('files', []))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return files

def download_file(file_id, file_name, dest_dir):
    request = service.files().get_media(fileId=file_id)
    os.makedirs(dest_dir, exist_ok=True)
    file_path = os.path.join(dest_dir, file_name)
    fh = io.FileIO(file_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
        print(f"Baixando {file_name}... {int(status.progress() * 100)}%")
    fh.close()
    print(f"✅ {file_name} salvo em {file_path}")

def main():
    print(f"Listando arquivos na pasta {FOLDER_ID}...")
    files = list_files_in_folder(FOLDER_ID)
    print(f"Total de arquivos encontrados: {len(files)}\n")
    for f in files:
        print(f"Baixando: {f['name']} (ID: {f['id']})")
        download_file(f['id'], f['name'], DEST_DIR)

if __name__ == "__main__":
    main()
