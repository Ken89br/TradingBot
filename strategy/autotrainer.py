#Função principal: Automatizar o fluxo completo de coleta de dados, disparo de treinamento, e upload para o Google Drive.
#O que faz:
#Busca dados de candles para vários símbolos/timeframes utilizando um cliente externo (dukascopy_client.cjs).
#Salva esses dados em CSV.
#Faz upload dos CSVs e modelos para o Google Drive.
#Periodicamente dispara o treinamento do modelo histórico (train_model_historic.main()).
#Roda em loop continuamente, mantendo os dados e modelos sempre atualizados.

# strategy/autotrainer.py
import os
import time
import json
import subprocess
import glob
from dotenv import load_dotenv
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import md5

from strategy.train_model_historic import main as run_training
from config import CONFIG
from data.google_drive_client import upload_or_update_file as upload_file, get_folder_id_for_file

load_dotenv()

# Configurações
SYMBOLS = CONFIG["symbols"] + CONFIG.get("otc_symbols", [])
TIMEFRAMES = CONFIG["timeframes"]
DATA_DIR = "data"
MODEL_DIR = "models"
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

BOOTSTRAP_FLAG = os.path.join(DATA_DIR, "autotrainer_bootstrap.flag")
LAST_RETRAIN_PATH = os.path.join(DATA_DIR, "last_retrain.txt")
LOG_FILE = os.path.join(DATA_DIR, "autotrainer.log")
FILE_HASHES_PATH = os.path.join(DATA_DIR, "autotrainer_uploaded_hashes.json")

# Logging estruturado
def setup_logging():
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# Utilitário para hash de arquivo
def file_md5(path):
    hash_md5 = md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Erro ao calcular hash de {path}: {str(e)}")
        return None

# Carrega/Sava hashes de uploads para evitar uploads repetidos
def load_uploaded_hashes():
    if os.path.exists(FILE_HASHES_PATH):
        try:
            with open(FILE_HASHES_PATH, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar hashes: {str(e)}")
    return {}

def save_uploaded_hashes(hashes):
    try:
        with open(FILE_HASHES_PATH, "w") as f:
            json.dump(hashes, f)
    except Exception as e:
        logger.error(f"Erro ao salvar hashes: {str(e)}")

uploaded_hashes = load_uploaded_hashes()

def fetch_and_save(symbol: str, from_dt: datetime, to_dt: datetime, tf: str) -> bool:
    """Busca e salva dados do Dukascopy com tratamento robusto de erros"""
    try:
        symbol_clean = symbol.lower().replace(" ", "").replace("/", "")
        cmd = [
            "node", "data/dukascopy_client.cjs",
            symbol_clean, tf.lower(),
            from_dt.isoformat(), to_dt.isoformat()
        ]
        logger.info(f"Fetching {symbol} {tf} from {from_dt} to {to_dt}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            check=True
        )

        candles = json.loads(result.stdout)
        if not candles:
            logger.warning(f"No candles for {symbol} @ {tf}")
            return False

        filename = f"{symbol_clean}_{tf.lower()}.csv"
        filepath = os.path.join(DATA_DIR, filename)

        # Decide se escreve cabeçalho
        write_header = not os.path.exists(filepath)
        with open(filepath, "a") as f:
            if write_header:
                f.write("timestamp,open,high,low,close,volume\n")
            for c in candles:
                f.write(f"{c['timestamp']},{c['open']},{c['high']},{c['low']},{c['close']},{c['volume']}\n")

        logger.info(f"Saved {len(candles)} rows to {filename}")
        return True

    except subprocess.TimeoutExpired:
        logger.error(f"Timeout fetching {symbol} @ {tf}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed for {symbol} @ {tf}: {e.stderr}")
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON response for {symbol} @ {tf}")
    except Exception as e:
        logger.error(f"Unexpected error with {symbol} @ {tf}: {str(e)}", exc_info=True)

    return False

def fetch_all_symbols_timeframes(from_dt: datetime, to_dt: datetime, max_workers: int = 6):
    """Paraleliza a coleta usando ThreadPoolExecutor"""
    jobs = []
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for symbol in SYMBOLS:
            for tf in TIMEFRAMES:
                job = executor.submit(fetch_and_save, symbol, from_dt, to_dt, tf)
                jobs.append(((symbol, tf), job))
        for (symbol, tf), job in jobs:
            try:
                results[(symbol, tf)] = job.result()
            except Exception as e:
                logger.error(f"Erro no fetch {symbol} {tf}: {str(e)}")
    return results

def bootstrap_initial_data():
    """Carrega dados históricos iniciais"""
    if os.path.exists(BOOTSTRAP_FLAG):
        return

    logger.info("Bootstrapping initial data (last 7 days)")
    now = datetime.utcnow()
    from_dt = now - timedelta(days=7)
    fetch_all_symbols_timeframes(from_dt, now)
    with open(BOOTSTRAP_FLAG, "w") as f:
        f.write(now.isoformat())
    logger.info("Bootstrap complete.")

def should_retrain() -> bool:
    if not os.path.exists(LAST_RETRAIN_PATH):
        return True
    try:
        with open(LAST_RETRAIN_PATH, "r") as f:
            last = datetime.fromisoformat(f.read().strip())
        return (datetime.utcnow() - last).total_seconds() >= 120
    except Exception as e:
        logger.error(f"Error reading last retrain time: {str(e)}")
        return True

def store_last_retrain_time():
    now = datetime.utcnow().isoformat()
    with open(LAST_RETRAIN_PATH, "w") as f:
        f.write(now)
    try:
        upload_file(LAST_RETRAIN_PATH)
        logger.info("Updated last retrain time on Drive")
    except Exception as e:
        logger.error(f"Failed to upload retrain time: {str(e)}")

def upload_files_parallel(pattern: str, description: str, max_workers: int = 4):
    """Upload paralelo e inteligente: só arquivos novos/alterados sobem"""
    files = glob.glob(pattern)
    jobs = []
    uploaded = 0
    changed_hashes = False
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for filepath in files:
            filename = os.path.basename(filepath)
            file_hash = file_md5(filepath)
            if not file_hash:
                continue
            # Só faz upload se mudou
            if uploaded_hashes.get(filename) == file_hash:
                logger.info(f"Skip upload (not changed): {filename}")
                continue
            jobs.append(executor.submit(upload_file, filepath))
            uploaded_hashes[filename] = file_hash  # Marca como enviado
            changed_hashes = True
        for idx, job in enumerate(jobs):
            try:
                file_id = job.result()
                logger.info(f"Uploaded {description}: {files[idx]} (ID: {file_id})")
                uploaded += 1
            except Exception as e:
                logger.error(f"Failed to upload {files[idx]}: {str(e)}")
    if changed_hashes:
        save_uploaded_hashes(uploaded_hashes)
    return uploaded

def main_loop():
    """Loop principal de execução"""
    bootstrap_initial_data()

    while True:
        cycle_start = datetime.utcnow()
        logger.info(f"Starting new cycle at {cycle_start.isoformat()}")

        # 1. Coleta de dados (paralelizada)
        fetch_start = cycle_start - timedelta(seconds=30)
        fetch_results = fetch_all_symbols_timeframes(fetch_start, cycle_start)
        success_count = sum(1 for v in fetch_results.values() if v)
        logger.info(f"Fetch complete: {success_count} datasets updated.")

        # 2. Upload de dados (paralelo/inteligente)
        uploaded_csv = upload_files_parallel(f"{DATA_DIR}/*.csv", "CSV files")
        logger.info(f"Uploaded {uploaded_csv} CSV files.")

        # 3. Treinamento condicional
        if should_retrain():
            try:
                logger.info("Starting model training...")
                run_training()
                store_last_retrain_time()
                uploaded_models = upload_files_parallel(f"{MODEL_DIR}/model_*.pkl", "model files")
                logger.info(f"Uploaded {uploaded_models} model files.")
            except Exception as e:
                logger.error(f"Training failed: {str(e)}", exc_info=True)
        else:
            logger.info("Skipping training - not time yet")

        # 4. Controle de ciclo
        cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
        sleep_time = max(1, 30 - cycle_duration)
        logger.info(f"Cycle completed in {cycle_duration:.2f}s. Sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)

def main():
    try:
        logger.info("Starting AutoTrainer service")
        main_loop()
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
