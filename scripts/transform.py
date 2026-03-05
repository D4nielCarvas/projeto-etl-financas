# Python
import logging
import pandas as pd
import pandera.pandas as pa

logger = logging.getLogger(__name__)

SCHEMA_VENDAS = pa.DataFrameSchema(
    {
        "id_transacao": pa.Column(pa.Int, coerce=True),
        "data_venda": pa.Column(pa.DateTime, coerce=True),
        "produto": pa.Column(pa.String, coerce=True),
        # Check garante que não existam vendas com valor negativo
        "valor_brl": pa.Column(pa.Float, checks=pa.Check.ge(0), coerce=True),
    }
)


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicatas, nulos e padroniza campos de texto/data."""
    # Separar responsabilidade de limpeza em função própria (SRP)
    df = df.drop_duplicates().copy()
    df = df.dropna(subset=["valor_brl"]).copy()

    if "produto" in df.columns:
        df["produto"] = df["produto"].str.strip().str.title()

    if "data_venda" in df.columns:
        df["data_venda"] = pd.to_datetime(df["data_venda"])

    df.reset_index(drop=True, inplace=True)
    return df


def _convert_currencies(df: pd.DataFrame, cotacoes: dict) -> pd.DataFrame:
    """Converte valor_brl para USD e EUR com base nas cotações fornecidas."""
    usd_rate = cotacoes.get("USD")
    eur_rate = cotacoes.get("EUR")

    # Validação explícita das taxas: evita TypeError ou ZeroDivisionError silencioso
    if not usd_rate or not eur_rate:
        raise ValueError(
            f"Cotações inválidas ou ausentes: USD={usd_rate}, EUR={eur_rate}"
        )

    df["valor_usd"] = round(df["valor_brl"] / usd_rate, 2)
    df["valor_eur"] = round(df["valor_brl"] / eur_rate, 2)
    return df


def _categorize_value_range(df: pd.DataFrame) -> pd.DataFrame:
    """Cria coluna faixa_valor com limites dinâmicos via percentis (p33 e p66)."""
    p33 = df["valor_brl"].quantile(0.33)
    p66 = df["valor_brl"].quantile(0.66)

    df["faixa_valor"] = pd.cut(
        df["valor_brl"],
        bins=[0, p33, p66, float("inf")],
        labels=["Small", "Medium", "High"],
    )
    return df


def transform_data(df: pd.DataFrame, cotacoes: dict) -> pd.DataFrame:
    # Passo 1: Limpeza e padronização
    df_transformed = _clean_dataframe(df)
    logger.info("Limpeza concluída: %d registros válidos.", len(df_transformed))

    # Passo 2: Validação de contrato de dados com Pandera
    df_transformed = SCHEMA_VENDAS.validate(df_transformed)
    logger.info("Validação de schema concluída com sucesso.")

    # Passo 3: Conversão de moedas
    df_transformed = _convert_currencies(df_transformed, cotacoes)

    # Passo 4: Categorização por faixa de valor (numeração corrigida — estava duplicada)
    df_transformed = _categorize_value_range(df_transformed)
    logger.info("Transformação finalizada: %d registros prontos.", len(df_transformed))

    return df_transformed
