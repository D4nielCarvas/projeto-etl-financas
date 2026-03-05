import logging
import os
import sys

from extract import extract_api_data, extract_csv_data
from flowchart import generate_etl_dashboard
from load import load_data_to_sqlite
from transform import transform_data

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Caminhos extraídos como constantes: facilita configuração sem alterar lógica
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_SCRIPT_DIR)
DEFAULT_CSV_PATH = os.path.join(_PROJECT_DIR, "data", "transacoes_vendas.csv")
DEFAULT_DB_PATH = os.path.join(_PROJECT_DIR, "data", "vendas.db")
DEFAULT_TABLE = "tb_vendas_convertidas"


def run_etl(
    csv_path: str = DEFAULT_CSV_PATH,
    db_path: str = DEFAULT_DB_PATH,
    table_name: str = DEFAULT_TABLE,
) -> None:
    logger.info("--- Iniciando o processo ETL ---")
    
    try:
        # [E] EXTRAÇÃO
        logger.info("1. Extração (Extract)...")
        cotacoes = extract_api_data()
        logger.info(
            "Cotações obtidas: Dólar = R$%.2f | Euro = R$%.2f",
            cotacoes["USD"],
            cotacoes["EUR"],
        )

        df_raw = extract_csv_data(csv_path)
        logger.info("Lidas %d transações do CSV bruto.", len(df_raw))

        # [T] TRANSFORMAÇÃO
        logger.info("2. Transformação (Transform)...")
        df_transformed = transform_data(df_raw, cotacoes)
        logger.info(
            "Dados limpos: %d registros após remoção de duplicatas/nulos.",
            len(df_transformed),
        )

        # [L] CARGA
        logger.info("3. Carga (Load)...")
        load_data_to_sqlite(df_transformed, db_path=db_path, table_name=table_name)
        logger.info("--- Processo ETL finalizado com SUCESSO! ---")

        # [V] VISUALIZAÇÃO — agora dentro do try/except para capturar falhas
        logger.info("4. Visualização (View) — Gerando dashboard...")
        generate_etl_dashboard(db_path=db_path)

    except Exception as e:
        # Re-raise após logar: o erro sobe para o chamador e não é engolido silenciosamente
        logger.error("O pipeline falhou: %s", e, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        run_etl()
    except Exception:
        # sys.exit(1) sinaliza falha ao sistema operacional (útil em CI/CD e agendadores)
        sys.exit(1)
