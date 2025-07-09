import os
import requests
import zipfile
import io
import pandas as pd
from datetime import datetime
from data.google_drive_client import upload_or_update_file

# ====== CONFIGURAÇÕES ======
LOCAL_COT_DIR = "cot_data"
os.makedirs(LOCAL_COT_DIR, exist_ok=True)

COT_URL = "https://www.cftc.gov/files/dea/history/fut_disagg_txt_2024.zip"
COT_ZIP_PATH = os.path.join(LOCAL_COT_DIR, "fut_disagg_txt_2024.zip")
COT_CSV_PATH = os.path.join(LOCAL_COT_DIR, "fut_disagg_2024.txt")
COT_PARSED_PATH = os.path.join(LOCAL_COT_DIR, "cot_parsed_2024.csv")

GDRIVE_FOLDER_ID = "17Ok0Eo53XvoUYKtr5iMPgd_NkXLtDT85"

COT_SYMBOL_MAP = {
    "EURUSD": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "GBPUSD": "BRITISH POUND STERLING - CHICAGO MERCANTILE EXCHANGE",
    "USDJPY": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "AUDUSD": "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "USDCHF": "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE",
    "NZDUSD": "NEW ZEALAND DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "USDCAD": "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "EURJPY": "EURO FX - CHICAGO MERCANTILE EXCHANGE",      # Não existe contrato direto, usa EURO
    "EURNZD": "EURO FX - CHICAGO MERCANTILE EXCHANGE",      # Não existe contrato direto, usa EURO
    "AEDCNY": None,                                         # Não existe contrato na CME/CFTC
    "AUDCAD": "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",  # Não existe direto, usa AUD
    "AUDCHF": "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",  # Não existe direto, usa AUD
    "AUDNZD": "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",  # Não existe direto, usa AUD
    "CADJPY": "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",    # Não existe direto, usa CAD
    "CHFJPY": "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE",        # Não existe direto, usa CHF
    "EURGBP": "EURO FX - CHICAGO MERCANTILE EXCHANGE",            # Não existe direto, usa EURO
}

print("Baixando arquivo COT da CFTC...")
r = requests.get(COT_URL)
with open(COT_ZIP_PATH, 'wb') as f:
    f.write(r.content)
print("Download concluído.")

print("Extraindo arquivo...")
with zipfile.ZipFile(COT_ZIP_PATH, 'r') as z:
    for name in z.namelist():
        if name.endswith('.txt'):
            z.extract(name, LOCAL_COT_DIR)
            os.rename(os.path.join(LOCAL_COT_DIR, name), COT_CSV_PATH)
            break
print("Arquivo extraído para:", COT_CSV_PATH)

print("Lendo arquivo COT...")
df_cot = pd.read_csv(COT_CSV_PATH, delimiter=',', encoding='latin1')
print("Linhas lidas:", len(df_cot))

rows = []
for my_symbol, cot_name in COT_SYMBOL_MAP.items():
    filtered = df_cot[df_cot['Market_and_Exchange_Names'] == cot_name]
    if filtered.empty:
        print(f"Aviso: Nenhum dado para {my_symbol} ({cot_name})")
        continue
    for _, row in filtered.iterrows():
        rows.append({
            "my_symbol": my_symbol,
            "cot_name": cot_name,
            "date": row['As_of_Date_In_Form_YYMMDD'],
            "net_long": row.get("Producer_Merchant_Processor_User_Long_All", None),
            "net_short": row.get("Producer_Merchant_Processor_User_Short_All", None),
            "open_interest": row.get("Open_Interest_All", None),
    
        })
df_parsed = pd.DataFrame(rows)
df_parsed.to_csv(COT_PARSED_PATH, index=False)
print("Arquivo CSV reduzido salvo em:", COT_PARSED_PATH)

print("Enviando arquivo parseado ao Google Drive...")
try:
    gdrive_file_id = upload_or_update_file(COT_PARSED_PATH, drive_folder_id=GDRIVE_FOLDER_ID)
    print(f"Upload concluído! File ID: {gdrive_file_id}")
except Exception as e:
    print("Falha no upload para o Google Drive:", e)
