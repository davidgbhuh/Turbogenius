"""Plotly chart builders for stock analysis."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from config import MA_WINDOWS, MA_COLORS, COLOR_UP, COLOR_DOWN, RSI_OVERBOUGHT, RSI_OVERSOLD


def candlestick_chart(df: pd.DataFrame, company_name: str = "") -> go.Figure:
    """Build candlestick chart with volume bars and moving averages."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25],
    )

    # Candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color=COLOR_UP,
            decreasing_line_color=COLOR_DOWN,
            increasing_fillcolor=COLOR_UP,
            decreasing_fillcolor=COLOR_DOWN,
            name="주가",
        ),
        row=1, col=1,
    )

    # Moving averages
    for window in MA_WINDOWS:
        col = f"MA{window}"
        if col in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df[col],
                    mode="lines",
                    name=f"MA{window}",
                    line=dict(color=MA_COLORS[window], width=1.2),
                ),
                row=1, col=1,
            )

    # Volume bars
    colors = [COLOR_UP if c >= o else COLOR_DOWN for c, o in zip(df["Close"], df["Open"])]
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df["Volume"],
            name="거래량",
            marker_color=colors,
            opacity=0.7,
        ),
        row=2, col=1,
    )

    title = f"{company_name} 주가 차트" if company_name else "주가 차트"
    fig.update_layout(
        title=title,
        xaxis_rangeslider_visible=False,
        height=500,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
    )
    fig.update_xaxes(gridcolor="#1e2130", showgrid=True)
    fig.update_yaxes(gridcolor="#1e2130", showgrid=True)
    return fig


def rsi_chart(df: pd.DataFrame) -> go.Figure:
    """Build RSI chart with overbought/oversold bands."""
    fig = go.Figure()

    fig.add_hrect(
        y0=RSI_OVERBOUGHT, y1=100,
        fillcolor="rgba(255, 59, 48, 0.1)", line_width=0,
        annotation_text="과매수", annotation_position="top right",
    )
    fig.add_hrect(
        y0=0, y1=RSI_OVERSOLD,
        fillcolor="rgba(0, 122, 255, 0.1)", line_width=0,
        annotation_text="과매도", annotation_position="bottom right",
    )
    fig.add_hline(y=RSI_OVERBOUGHT, line_dash="dash", line_color=COLOR_UP, line_width=1)
    fig.add_hline(y=RSI_OVERSOLD, line_dash="dash", line_color=COLOR_DOWN, line_width=1)
    fig.add_hline(y=50, line_dash="dot", line_color="#888", line_width=1)

    if "RSI" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["RSI"],
            mode="lines", name="RSI",
            line=dict(color="#FF9500", width=2),
        ))

    fig.update_layout(
        title="RSI (14)",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(range=[0, 100]),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
    )
    fig.update_xaxes(gridcolor="#1e2130")
    fig.update_yaxes(gridcolor="#1e2130")
    return fig


def macd_chart(df: pd.DataFrame) -> go.Figure:
    """Build MACD line + signal + histogram chart."""
    fig = make_subplots(rows=1, cols=1)

    if "MACD_hist" in df.columns:
        hist_colors = [COLOR_UP if v >= 0 else COLOR_DOWN for v in df["MACD_hist"].fillna(0)]
        fig.add_trace(go.Bar(
            x=df.index, y=df["MACD_hist"],
            name="히스토그램",
            marker_color=hist_colors,
            opacity=0.7,
        ))

    if "MACD" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD"],
            mode="lines", name="MACD",
            line=dict(color="#007AFF", width=1.5),
        ))

    if "MACD_signal" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["MACD_signal"],
            mode="lines", name="시그널",
            line=dict(color="#FF9500", width=1.5),
        ))

    fig.update_layout(
        title="MACD (12, 26, 9)",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
    )
    fig.update_xaxes(gridcolor="#1e2130")
    fig.update_yaxes(gridcolor="#1e2130")
    return fig


def bollinger_chart(df: pd.DataFrame) -> go.Figure:
    """Build Bollinger Band chart."""
    fig = go.Figure()

    if "BB_upper" in df.columns and "BB_lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_upper"],
            mode="lines", name="상단밴드",
            line=dict(color="rgba(175, 82, 222, 0.6)", width=1),
        ))
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_lower"],
            mode="lines", name="하단밴드",
            line=dict(color="rgba(175, 82, 222, 0.6)", width=1),
            fill="tonexty",
            fillcolor="rgba(175, 82, 222, 0.05)",
        ))
    if "BB_mid" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["BB_mid"],
            mode="lines", name="중간밴드",
            line=dict(color="rgba(175, 82, 222, 1)", width=1.5, dash="dash"),
        ))

    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"],
        mode="lines", name="종가",
        line=dict(color="#fafafa", width=1.5),
    ))

    fig.update_layout(
        title="볼린저밴드 (20, 2)",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="#fafafa"),
    )
    fig.update_xaxes(gridcolor="#1e2130")
    fig.update_yaxes(gridcolor="#1e2130")
    return fig
