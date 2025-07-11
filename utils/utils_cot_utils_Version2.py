import os
import pandas as pd
from data.google_drive_client import download_file, get_folder_id_for_file

COT_DATA_DIR = "cot_data"

def get_latest_cot_file():
    """Encontra o arquivo cot_processed mais recente na pasta cot_data."""
    if not os.path.exists(COT_DATA_DIR):
        os.makedirs(COT_DATA_DIR, exist_ok=True)
    files = [f for f in os.listdir(COT_DATA_DIR) if f.startswith("cot_processed_") and f.endswith(".csv")]
    if not files:
        return None
    latest_file = sorted(files)[-1]
    return os.path.join(COT_DATA_DIR, latest_file)

def ensure_latest_cot_local():
    """
    Garante que o arquivo COT mais recente está disponível localmente.
    Se não houver arquivo, tenta baixar do Google Drive.
    """
    latest_file = get_latest_cot_file()
    if latest_file is not None and os.path.exists(latest_file):
        return latest_file
    # Tenta baixar do Google Drive se estiver vazio/localmente ausente
    try:
        # Nome padrão do arquivo mais recente (ajuste se preferir)
        # Exemplo: "cot_processed_20250711_1030.csv"
        # Você pode também listar arquivos do Drive para pegar o mais recente, se quiser.
        filename = "cot_processed_20250711_1030.csv"  # Troque para automatizar!
        dest = os.path.join(COT_DATA_DIR, filename)
        download_file(filename, dest, drive_folder_id=get_folder_id_for_file(filename))
        if os.path.exists(dest):
            return dest
    except Exception as e:
        print(f"[COT UTILS] Falha ao baixar arquivo COT do Drive: {e}")
    return None

def get_latest_cot(symbol):
    """
    Busca o valor COT mais recente para o símbolo informado.
    Retorna dict com net_position, pct_long, open_interest, date.
    """
    csv_path = ensure_latest_cot_local()
    if not csv_path or not os.path.exists(csv_path):
        print("[COT UTILS] Nenhum arquivo COT disponível localmente.")
        return None
    try:
        df = pd.read_csv(csv_path)
        df_symbol = df[df['my_symbol'] == symbol]
        if df_symbol.empty:
            return None
        row = df_symbol.sort_values("date").iloc[-1]
        return {
            "net_position": row["net_position"],
            "pct_long": row["pct_long"],
            "open_interest": row["Open_Interest_All"],
            "date": row["date"]
        }
    except Exception as e:
        print(f"[COT UTILS] Erro ao ler COT: {e}")
        return None