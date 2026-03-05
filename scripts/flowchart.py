import logging
import os

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

# ── Constantes de estilo ─────────────────────────────────────────────────────
BG_DARK   = "#1A1A2E"
BG_PAPER  = "#16213E"
TEXT      = "#E0E0E0"
GRID      = "#2A2A4A"
FAIXAS    = ["Small", "Medium", "High"]
COLORS = {
    "Small":  "#4A90D9",
    "Medium": "#E07B39",
    "High":   "#9B59B6",
    "brl":    "#4CAF76",
    "usd":    "#4A90D9",
    "eur":    "#E07B39",
}


# ── Carregamento ─────────────────────────────────────────────────────────────
def _load_dataframe(db_path: str, table_name: str) -> pd.DataFrame:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        df = pd.read_sql(f"SELECT * FROM {table_name}", con=engine)  # noqa: S608
        df["data_venda"] = pd.to_datetime(df["data_venda"])
        return df
    finally:
        engine.dispose()


# ── KPI traces ───────────────────────────────────────────────────────────────
def _build_kpi_traces(fig: go.Figure, df: pd.DataFrame) -> None:
    total_brl    = df["valor_brl"].sum()
    total_usd    = df["valor_usd"].sum()
    total_eur    = df["valor_eur"].sum()
    n_trans      = len(df)
    ticket_medio = df["valor_brl"].mean()

    kpis = [
        (
            total_brl, "R$ ", COLORS["brl"],
            f"Receita Total (BRL)<br><sup>{n_trans} transações</sup>",
            {
                "reference":  ticket_medio * n_trans * 0.9,
                "relative":   True,
                "valueformat": ".1%",
                "increasing": {"color": COLORS["brl"]},
            },
        ),
        (total_usd, "$ ",  COLORS["usd"], "Receita Total (USD)<br><sup>Conversão via AwesomeAPI</sup>", None),
        (total_eur, "€ ",  COLORS["eur"], "Receita Total (EUR)<br><sup>Conversão via AwesomeAPI</sup>", None),
    ]

    for col, (value, prefix, color, title, delta) in enumerate(kpis, start=1):
        trace = go.Indicator(
            mode="number+delta" if delta else "number",
            value=value,
            number={"prefix": prefix, "valueformat": ",.2f", "font": {"size": 36, "color": color}},
            title={"text": title, "font": {"color": TEXT, "size": 13}},
            **({"delta": delta} if delta else {}),
        )
        fig.add_trace(trace, row=1, col=col)


# ── Gráficos analíticos ──────────────────────────────────────────────────────
def _build_chart_traces(fig: go.Figure, df: pd.DataFrame) -> None:
    faixa_counts = df["faixa_valor"].value_counts().reindex(FAIXAS)
    time_series  = df.groupby("data_venda")["valor_brl"].sum().reset_index()

    prod_revenue = (
        df.groupby("produto")["valor_brl"]
        .sum()
        .sort_values(ascending=False)
        .head(15)
        .sort_values(ascending=True)   # inverte para barras horizontais lerem de baixo p/ cima
    )

    # ── Rosca: faixa_valor ───────────────────────────────────────────────────
    fig.add_trace(
        go.Pie(
            labels=faixa_counts.index.tolist(),
            values=faixa_counts.values,
            hole=0.52,
            marker_colors=[COLORS[f] for f in FAIXAS],
            textfont={"color": "white", "size": 13},
            hovertemplate="%{label}<br>Qtd: %{value}<br>%{percent}<extra></extra>",
            showlegend=False,   # ← corrige "trace 4" na legenda
        ),
        row=2, col=1,
    )

    # ── Barras horizontais: receita por produto ──────────────────────────────
    fig.add_trace(
        go.Bar(
            y=prod_revenue.index.tolist(),
            x=prod_revenue.values,
            orientation="h",
            marker=dict(
                color=prod_revenue.values,
                colorscale=[[0, "#4A90D9"], [0.5, "#E07B39"], [1, "#9B59B6"]],
                showscale=False,
            ),

            text=[f"R$ {v:,.0f}" for v in prod_revenue.values],
            textposition="auto",
            textfont={"color": "white", "size": 10},
            hovertemplate="%{y}<br>R$ %{x:,.2f}<extra></extra>",
            showlegend=False,
        ),
        row=2, col=2,
    )

    time_weekly = (
        time_series.set_index("data_venda")["valor_brl"]
        .resample("W")
        .sum()
        .reset_index()
    )
    fig.add_trace(
        go.Scatter(
            x=time_weekly["data_venda"],
            y=time_weekly["valor_brl"],
            mode="lines+markers",
            line=dict(color=COLORS["brl"], width=2.5),

            marker=dict(size=6, color=COLORS["brl"], line=dict(color="white", width=1)),
            fill="tozeroy",
            fillcolor="rgba(76, 175, 118, 0.12)",
            hovertemplate="%{x|%d/%m/%Y}<br>R$ %{y:,.2f}<extra></extra>",

            showlegend=False,
        ),
        row=2, col=3,
    )

    # ── Barras agrupadas: receita por moeda ──────────────────────────────────
    for moeda, col_key, prefix in [("BRL", "brl", "R$"), ("USD", "usd", "$"), ("EUR", "eur", "€")]:
        col_name = f"valor_{moeda.lower()}"
        vals = [df[df["faixa_valor"] == f][col_name].sum() for f in FAIXAS]
        fig.add_trace(
            go.Bar(
                name=moeda,
                x=FAIXAS,
                y=vals,
                marker_color=COLORS[col_key],
                hovertemplate=f"%{{x}}<br>{prefix} %{{y:,.2f}} {moeda}<extra></extra>",
            ),
            row=3, col=1,
        )

    # ── Barras: contagem por faixa ───────────────────────────────────────────
    fig.add_trace(
        go.Bar(
            x=faixa_counts.index.tolist(),
            y=faixa_counts.values,
            marker_color=[COLORS[f] for f in FAIXAS],
            text=faixa_counts.values,
            textposition="outside",
            textfont={"color": TEXT},
            hovertemplate="%{x}<br>%{y} transações<extra></extra>",
            showlegend=False,
        ),
        row=3, col=2,
    )

    # ── Barras: ticket médio por faixa ───────────────────────────────────────
    ticket_faixa = df.groupby("faixa_valor")["valor_brl"].mean().reindex(FAIXAS)
    fig.add_trace(
        go.Bar(
            x=ticket_faixa.index.tolist(),
            y=ticket_faixa.values,
            marker_color=[COLORS[f] for f in FAIXAS],
            text=[f"R$ {v:,.2f}" for v in ticket_faixa.values],
            textposition="outside",
            textfont={"color": TEXT},
            hovertemplate="%{x}<br>Ticket médio: R$ %{y:,.2f}<extra></extra>",
            showlegend=False,
        ),
        row=3, col=3,
    )


# ── Função principal ─────────────────────────────────────────────────────────
def generate_etl_dashboard(db_path: str, table_name: str = "tb_vendas_convertidas") -> None:
    df = _load_dataframe(db_path, table_name)

    fig = make_subplots(
        rows=3, cols=3,
        row_heights=[0.18, 0.45, 0.37],   # ← KPIs menores, gráficos maiores
        specs=[
            [{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}],
            [{"type": "pie"},       {"type": "bar"},        {"type": "scatter"}],
            [{"type": "bar"},       {"type": "bar"},        {"type": "bar"}],
        ],
        subplot_titles=(
            "", "", "",
            "Distribuição por Faixa de Valor",
            "Top 15 — Receita por Produto (BRL)",   # ← título atualizado
            "Evolução Semanal das Vendas",           # ← reflete o resample semanal
            "Receita Total por Moeda",
            "Qtd. de Transações por Faixa",
            "Ticket Médio por Faixa (BRL)",
        ),
        vertical_spacing=0.09,
        horizontal_spacing=0.08,
    )

    _build_kpi_traces(fig, df)
    _build_chart_traces(fig, df)

    fig.update_yaxes(type="log", row=3, col=1)

    fig.update_layout(
        title=dict(
            text=(
                "📊 Dashboard ETL — Resultados das Transações Financeiras"
                "<br><sup>Pipeline: Extract → Transform → Load → View</sup>"
            ),
            x=0.5, xanchor="center",
            font=dict(size=20, color="white", family="Inter, Arial, sans-serif"),
        ),
        plot_bgcolor=BG_DARK,
        paper_bgcolor=BG_PAPER,
        font=dict(color=TEXT, family="Inter, Arial, sans-serif"),
        legend=dict(
            title=dict(text="Moeda", font=dict(size=13, color="#AAAAAA")),
            bgcolor="rgba(255,255,255,0.05)",
            bordercolor="#444",
            borderwidth=1,
            font=dict(color=TEXT),
            orientation="v",
            x=1.01,
            y=0.5,
        ),
        barmode="group",
        height=950,
        margin=dict(l=50, r=100, t=110, b=50),
    )

    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=TEXT))
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, tickfont=dict(color=TEXT))

    # Títulos dos eixos
    fig.update_xaxes(title_text="Receita (R$)",   title_font=dict(size=11, color="#AAAAAA"), row=2, col=2)
    fig.update_yaxes(title_text="Produto",         title_font=dict(size=11, color="#AAAAAA"), row=2, col=2)
    fig.update_xaxes(title_text="Semana",          title_font=dict(size=11, color="#AAAAAA"), row=2, col=3)
    fig.update_yaxes(title_text="Receita (R$)",    title_font=dict(size=11, color="#AAAAAA"), row=2, col=3)
    fig.update_xaxes(title_text="Faixa de Valor",  title_font=dict(size=11, color="#AAAAAA"), row=3, col=1)
    fig.update_yaxes(title_text="Receita (log)",   title_font=dict(size=11, color="#AAAAAA"), row=3, col=1)
    fig.update_xaxes(title_text="Faixa de Valor",  title_font=dict(size=11, color="#AAAAAA"), row=3, col=2)
    fig.update_yaxes(title_text="Qtd. Transações", title_font=dict(size=11, color="#AAAAAA"), row=3, col=2)
    fig.update_xaxes(title_text="Faixa de Valor",  title_font=dict(size=11, color="#AAAAAA"), row=3, col=3)
    fig.update_yaxes(title_text="Ticket Médio (R$)", title_font=dict(size=11, color="#AAAAAA"), row=3, col=3)

    for ann in fig.layout.annotations:
        ann.font.color = "#CCCCCC"
        ann.font.size = 12

    logger.info("Dashboard gerado com sucesso.")
    fig.show()


if __name__ == "__main__":
    _script_dir  = os.path.dirname(os.path.abspath(__file__))
    _project_dir = os.path.dirname(_script_dir)
    _db_path     = os.path.join(_project_dir, "data", "vendas.db")
    generate_etl_dashboard(_db_path)
