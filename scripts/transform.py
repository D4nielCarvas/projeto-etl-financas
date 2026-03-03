import pandas as pd
import pandera.pandas as pa

def transform_data(df: pd.DataFrame, cotacoes: dict) -> pd.DataFrame:
    
    # 1. Removendo duplicatas baseadas em todas as colunas
    df_transformed = df.drop_duplicates().copy()
    
    # 2. Tratando valores nulos na coluna essencial (valor_brl)
    df_transformed = df_transformed.dropna(subset=['valor_brl']).copy()
    
    # Limpeza e padronização (Ex: removendo espaços extras e capitalizando)
    if 'produto' in df_transformed.columns:
        df_transformed['produto'] = df_transformed['produto'].str.strip().str.title()
        
    if 'data_venda' in df_transformed.columns:
        df_transformed['data_venda'] = pd.to_datetime(df_transformed['data_venda'])
    
    # Resetando index para ter uma tabela mais limpa
    df_transformed.reset_index(drop=True, inplace=True)
    
    # 3. VALIDAÇÃO DE QUALIDADE DE DADOS (PANDERA)
    # Define o contrato de dados: o que esperamos que o DataFrame contenha exatamente
    schema_vendas = pa.DataFrameSchema({
        "id_transacao": pa.Column(pa.Int, coerce=True),
        "data_venda": pa.Column(pa.DateTime, coerce=True),
        "produto": pa.Column(pa.String, coerce=True),
        "valor_brl": pa.Column(pa.Float, checks=pa.Check.ge(0), coerce=True) # Não pode haver vendas negativas
    })
    
    # Executa a validação rigorosa (Quebra o pipeline se os dados forem inválidos)
    df_transformed = schema_vendas.validate(df_transformed)
    
    # 4. Conversão de moedas
    usd_rate = cotacoes.get('USD')
    eur_rate = cotacoes.get('EUR')
    
    # Divisão pelo valor da cotação para achar o equivalente na moeda estrangeira (Cotação é BRL para 1 USD)
    df_transformed['valor_usd'] = round(df_transformed['valor_brl'] / usd_rate, 2)
    df_transformed['valor_eur'] = round(df_transformed['valor_brl'] / eur_rate, 2)
    
    # 4. Criando coluna categórica (faixa_valor) com pd.cut + thresholds dinâmicos
    # Os limites são calculados automaticamente via percentis (p33 e p66) do próprio dataset
    p33 = df_transformed['valor_brl'].quantile(0.33)
    p66 = df_transformed['valor_brl'].quantile(0.66)

    df_transformed['faixa_valor'] = pd.cut(
        df_transformed['valor_brl'],
        bins=[0, p33, p66, float('inf')],
        labels=['Small', 'Medium', 'High']
    )
    
    return df_transformed