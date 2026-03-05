# Python
import logging
import pandas as pd
import requests

# Constante no nível do módulo: facilita manutenção e testes (Open/Closed Principle)
API_URL = "https://economia.awesomeapi.com.br/last/USD-BRL,EUR-BRL"

# Timeout padrão em segundos para evitar que a requisição trave indefinidamente
REQUEST_TIMEOUT = 10

# Configura logging no lugar de print() — padrão profissional e rastreável
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def extract_api_data(url: str = API_URL, timeout: int = REQUEST_TIMEOUT) -> dict:
    # Adicionado timeout: evita hang infinito em redes instáveis (risco de segurança/disponibilidade)
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    # Uso explícito de try/except para KeyError: falha rápida com mensagem clara
    try:
        cotacoes = {
            "USD": float(data["USDBRL"]["bid"]),
            "EUR": float(data["EURBRL"]["bid"]),
        }
    except KeyError as e:
        raise KeyError(f"Chave inesperada no retorno da API: {e}") from e

    logger.info("Cotações extraídas com sucesso: %s", cotacoes)
    return cotacoes


def extract_csv_data(filepath: str) -> pd.DataFrame:
    # Validação explícita antes de tentar ler: mensagem de erro mais clara que a padrão do pandas
    import os
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {filepath}")

    df = pd.read_csv(filepath)
    logger.info("CSV carregado: %d linhas extraídas de '%s'.", len(df), filepath)
    return df


if __name__ == "__main__":
    logger.info("Testando extração da API...")
    logger.info(extract_api_data())
