import os
import json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.oauth2 import service_account
import io
import logging
from datetime import datetime

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

def upload_or_update_file(filepath, drive_folder_id=None, share_with_email=DEFAULT_SHARE_EMAIL):
    """
    Faz upload do arquivo, ou faz update do mesmo no Google Drive se ele já existir.
    Retorna o file_id do arquivo no Drive.
    """
    service = get_drive_service()
    filename = os.path.basename(filepath)
    if drive_folder_id is None:
        drive_folder_id = get_folder_id_for_file(filename)
    file_id = find_file_id(filename, drive_folder_id)
    file_metadata = {'name': filename}
    if drive_folder_id:
        file_metadata['parents'] = [drive_folder_id]
    media = MediaFileUpload(filepath, resumable=True)
    if file_id:
        # Atualiza arquivo existente (commit/update)
        updated_file = service.files().update(
            fileId=file_id,
            media_body=media
        ).execute()
        print(f"📝 Atualização concluída: {filename} (ID: {file_id})")
        if share_with_email:
            share_file_with_user(file_id, share_with_email)
        return file_id
    else:
        # Faz upload novo se não existir
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')
        print(f"✅ Upload concluído: {filename} (ID: {file_id})")
        if share_with_email:
            share_file_with_user(file_id, share_with_email)
        return file_id

def upload_or_update_all_files_in_directory(local_dir, share_with_email=DEFAULT_SHARE_EMAIL, extensions=('.csv', '.pkl')):
    """
    Processa todos arquivos do diretório especificado e faz upload/update no Drive.
    Gera log enriquecido com informações do arquivo.
    """
    total = 0
    updated = 0
    uploaded = 0
    for fname in os.listdir(local_dir):
        if fname.lower().endswith(extensions):
            fpath = os.path.join(local_dir, fname)
            filesize = os.path.getsize(fpath)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath)).strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n[INFO] Processando arquivo: {fname}")
            print(f"       Tamanho: {filesize/1024:.2f} KB")
            print(f"       Modificado em: {mtime}")
            service = get_drive_service()
            filename = os.path.basename(fpath)
            if fname.lower().endswith('.csv'):
                drive_folder_id = CSV_FOLDER_ID
            elif fname.lower().endswith('.pkl'):
                drive_folder_id = PKL_FOLDER_ID
            else:
                drive_folder_id = None
            file_id = find_file_id(filename, drive_folder_id)
            if file_id:
                upload_or_update_file(fpath, drive_folder_id, share_with_email)
                updated += 1
            else:
                upload_or_update_file(fpath, drive_folder_id, share_with_email)
                uploaded += 1
            total += 1
    print(f"\nResumo do processamento automático:")
    print(f"  Total de arquivos processados: {total}")
    print(f"  Arquivos atualizados (update): {updated}")
    print(f"  Arquivos enviados novos (upload): {uploaded}")

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

def list_files_in_drive_folder(drive_folder_id):
    service = get_drive_service()
    files = []
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{drive_folder_id}' in parents and trashed = false",
            spaces='drive',
            fields='nextPageToken, files(id, name, mimeType, modifiedTime, size)',
            pageToken=page_token
        ).execute()
        files.extend(response.get('files', []))
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    print(f"\nArquivos na pasta {drive_folder_id}:")
    for f in files:
        print(f"- {f['name']} (ID: {f['id']}, Modificado: {f.get('modifiedTime', '-')}, Tamanho: {f.get('size', '-')} bytes)")
    return files

# Exemplo de uso: processar todos arquivos no diretório 'data/' (ajuste conforme seu fluxo)
if __name__ == "__main__":
    local_dir = os.path.join(os.path.dirname(__file__), '.')  # Mude se necessário para o diretório correto
    print(f"Iniciando upload/update automático de arquivos do diretório: {local_dir}\n")
    upload_or_update_all_files_in_directory(local_dir)
    # (Opcional) Listar arquivos no Drive após upload
    print("\nArquivos .csv disponíveis no Google Drive:")
    list_files_in_drive_folder(CSV_FOLDER_ID)