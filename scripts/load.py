import logging
import pandas as pd
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)


def load_data_to_sqlite(
    df: pd.DataFrame,
    db_path: str,
    table_name: str,
    # Parâmetro if_exists exposto: permite 'replace', 'append' ou 'fail' sem alterar a função
    if_exists: str = "replace",
) -> None:
    # Criando a engine fora do bloco try para poder dar dispose() no finally
    engine = create_engine(f"sqlite:///{db_path}")

    try:
        # Código agora está DENTRO da função — indentação corrigida (era bug crítico)
        df.to_sql(name=table_name, con=engine, if_exists=if_exists, index=False)
        logger.info(
            "[%d linhas] carregadas com sucesso na tabela '%s' em '%s'.",
            len(df),
            table_name,
            db_path,
        )
    except Exception as e:
        # Propaga a exceção com contexto claro para o pipeline tratar
        logger.error("Falha ao carregar dados na tabela '%s': %s", table_name, e)
        raise
    finally:
        # Sempre libera a conexão com o banco, evitando vazamento de recursos
        engine.dispose()
