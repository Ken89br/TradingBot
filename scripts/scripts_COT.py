import os
import requests
import zipfile
import io
import pandas as pd
import logging
from datetime import datetime
from multiprocessing import Pool
import yaml
from typing import Dict, Optional
from bs4 import BeautifulSoup
import re

# Import do método de upload para o Google Drive
# Substitua pelo caminho real no seu projeto!
from data.google_drive_client import upload_or_update_file

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('cot_processor.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

class CotProcessor:
    def __init__(self, config_path: str = 'COT.yaml', gdrive_folder_id: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.local_cot_dir = "cot_data"
        self.gdrive_folder_id = gdrive_folder_id
        os.makedirs(self.local_cot_dir, exist_ok=True)
        
    def _load_config(self, config_path: str) -> Dict:
        """Carrega configurações de arquivo YAML"""
        try:
            with open(config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            raise

    def _get_latest_cot_url(self) -> str:
        """Busca o link mais recente do arquivo COT no site da CFTC"""
        page_url = "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm"
        logger.info(f"Buscando link automático do arquivo COT em {page_url} ...")
        resp = requests.get(page_url, timeout=20)
        soup = BeautifulSoup(resp.content, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link['href']
            # Padrão dos arquivos históricos de Futuros Desagregados
            if re.search(r'fut_disagg_txt_\d{4}\.zip', href):
                if href.startswith('/'):
                    href = "https://www.cftc.gov" + href
                logger.info(f"Link do arquivo encontrado: {href}")
                return href
        raise Exception("Arquivo COT (fut_disagg_txt_YYYY.zip) não encontrado.")

    def download_file(self, url: str, save_path: str) -> bool:
        """Baixa arquivo com tratamento de erros e retry"""
        try:
            logger.info(f"Iniciando download de {url}")
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            with open(save_path, 'wb') as f:
                f.write(r.content)
            logger.info(f"Arquivo salvo em {save_path}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Falha no download: {e}")
            return False

    def extract_and_process(self, zip_path: str) -> Optional[pd.DataFrame]:
        """Extrai e processa o arquivo COT"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                for name in z.namelist():
                    if name.endswith('.txt'):
                        with z.open(name) as f:
                            # Define tipos para otimizar memória
                            dtypes = {
                                'Market_and_Exchange_Names': 'category',
                                'As_of_Date_In_Form_YYMMDD': 'int32',
                                'Producer_Merchant_Processor_User_Long_All': 'float32',
                                'Producer_Merchant_Processor_User_Short_All': 'float32',
                                'Open_Interest_All': 'float32'
                            }
                            df_cot = pd.read_csv(f, delimiter=',', dtype=dtypes)
                            logger.info(f"Linhas lidas: {len(df_cot)}")
                            return df_cot
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair/processar: {e}")
            return None

    def process_symbol_data(self, args) -> Optional[pd.DataFrame]:
        """Processa dados para um símbolo específico"""
        symbol, cot_name = args
        if not cot_name:
            return None
        try:
            filtered = self.df_cot[self.df_cot['Market_and_Exchange_Names'] == cot_name]
            if filtered.empty:
                logger.warning(f"Nenhum dado para {symbol} ({cot_name})")
                return None
            result = filtered.assign(
                my_symbol=symbol,
                date=lambda x: pd.to_datetime(x['As_of_Date_In_Form_YYMMDD'], format='%y%m%d'),
                net_position=lambda x: x['Producer_Merchant_Processor_User_Long_All'] - 
                                     x['Producer_Merchant_Processor_User_Short_All'],
                pct_long=lambda x: x['Producer_Merchant_Processor_User_Long_All'] / 
                                   x['Open_Interest_All']
            )[['my_symbol', 'date', 'net_position', 'pct_long', 'Open_Interest_All']]
            return result
        except Exception as e:
            logger.error(f"Erro processando {symbol}: {e}")
            return None

    def run_pipeline(self):
        """Executa todo o pipeline de processamento"""
        try:
            # Busca dinâmica do link
            cot_url = self._get_latest_cot_url()
            cot_zip_path = os.path.join(self.local_cot_dir, "cot_latest.zip")
            if not self.download_file(cot_url, cot_zip_path):
                return False

            # Extração e processamento inicial
            self.df_cot = self.extract_and_process(cot_zip_path)
            if self.df_cot is None:
                return False

            # Processamento paralelo
            with Pool() as pool:
                results = pool.map(self.process_symbol_data, self.config['symbols'].items())
            
            # Combina resultados
            df_parsed = pd.concat([r for r in results if r is not None])
            
            # Salva arquivo com timestamp
            version = datetime.now().strftime("%Y%m%d_%H%M")
            output_path = os.path.join(self.local_cot_dir, f"cot_processed_{version}.csv")
            df_parsed.to_csv(output_path, index=False)
            logger.info(f"Dados processados salvos em {output_path}")

            # Upload para Google Drive (se folder id for fornecido)
            if self.gdrive_folder_id:
                logger.info("Enviando arquivo processado ao Google Drive...")
                try:
                    file_id = upload_or_update_file(output_path, drive_folder_id=self.gdrive_folder_id)
                    logger.info(f"Upload concluído! File ID: {file_id}")
                except Exception as e:
                    logger.error(f"Falha no upload para o Google Drive: {e}")

            return True
            
        except Exception as e:
            logger.error(f"Erro no pipeline: {e}")
            return False

if __name__ == "__main__":
    # Troque pelo ID real da sua pasta no Google Drive
    GDRIVE_FOLDER_ID = "17Ok0Eo53XvoUYKtr5iMPgd_NkXLtDT85"

    processor = CotProcessor(config_path="COT.yaml", gdrive_folder_id=GDRIVE_FOLDER_ID)
    if processor.run_pipeline():
        logger.info("Processamento concluído com sucesso!")
    else:
        logger.error("Falha no processamento")