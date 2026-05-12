"""ETF 분석 — 개별 시세·캔들·수익률 + 다중 비교."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import cumulative_returns, summary_metrics
from common import (
    default_date_range,
    etf_selector,
    fetch_close_panel,
    fetch_daily,
    load_etf_list,
    require_client,
)
from kis.quotes import get_current_price

st.set_page_config(page_title="ETF 분석", page_icon="🔎", layout="wide")
client = require_client()

st.title("🔎 ETF 분석")
st.caption("개별 ETF 캔들·지표 분석과 복수 ETF 정규화 비교를 한 페이지에서 수행합니다.")

tab_single, tab_compare = st.tabs(["개별 분석", "다중 비교"])

# ─────────────────────────── 개별 분석 ───────────────────────────────────
with tab_single:
    col_sel, col_range = st.columns([2, 3])
    with col_sel:
        code = etf_selector("ETF 선택", default_codes=["069500"], key="single_code")
    with col_range:
        default_start, default_end = default_date_range(2)
        start, end = st.date_input(
            "조회 기간",
            value=(default_start, default_end),
            max_value=default_end,
            key="single_range",
        )

    try:
        snap = get_current_price(client, code)
    except Exception as e:  # noqa: BLE001
        st.error(f"현재가 조회 실패: {e}")
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "현재가",
        f"{snap['price']:,.0f} 원",
        f"{snap['change']:+,.0f} ({snap['change_pct']:+.2f}%)",
    )
    m2.metric("시가", f"{snap['open']:,.0f}")
    m3.metric("고가 / 저가", f"{snap['high']:,.0f} / {snap['low']:,.0f}")
    m4.metric("거래량", f"{snap['volume']:,.0f}")

    try:
        df = fetch_daily(code, start, end)
    except Exception as e:  # noqa: BLE001
        st.error(f"기간별 시세 조회 실패: {e}")
        st.stop()
    if df.empty or len(df) < 2:
        st.info("선택한 기간의 데이터가 부족합니다.")
        st.stop()

    candle = go.Figure(
        data=[
            go.Candlestick(
                x=df.index,
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color="#ef4444",
                decreasing_line_color="#3b82f6",
                name="OHLC",
            )
        ]
    )
    candle.update_layout(
        xaxis_rangeslider_visible=False,
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        template="plotly_dark",
    )
    st.plotly_chart(candle, use_container_width=True)

    prices = df["close"]
    metrics = summary_metrics(prices)
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("총 수익률", f"{metrics['total_return'] * 100:+.2f}%")
    m2.metric("CAGR", f"{metrics['cagr'] * 100:+.2f}%")
    m3.metric("변동성(연)", f"{metrics['volatility'] * 100:.2f}%")
    m4.metric("MDD", f"{metrics['max_drawdown'] * 100:.2f}%")
    m5.metric("샤프", f"{metrics['sharpe']:.2f}")

    cum = cumulative_returns(prices)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=cum.index,
            y=cum.values * 100,
            mode="lines",
            line=dict(color="#22c55e", width=2),
            fill="tozeroy",
            name="누적 수익률 (%)",
        )
    )
    fig.update_layout(
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        template="plotly_dark",
        yaxis_title="%",
    )
    st.plotly_chart(fig, use_container_width=True)

    running_max = prices.cummax()
    dd = (prices / running_max - 1.0) * 100
    fig_dd = go.Figure()
    fig_dd.add_trace(
        go.Scatter(
            x=dd.index,
            y=dd.values,
            mode="lines",
            line=dict(color="#ef4444", width=1.5),
            fill="tozeroy",
            name="Drawdown (%)",
        )
    )
    fig_dd.update_layout(
        height=240,
        margin=dict(l=10, r=10, t=30, b=10),
        template="plotly_dark",
        yaxis_title="Drawdown (%)",
        title="Drawdown",
    )
    st.plotly_chart(fig_dd, use_container_width=True)

# ─────────────────────────── 다중 비교 ───────────────────────────────────
with tab_compare:
    cmp_codes = etf_selector(
        "비교할 ETF 선택 (2개 이상)",
        default_codes=["069500", "360750", "152380"],
        multi=True,
        key="cmp_codes",
    )
    cmp_start, cmp_end = st.date_input(
        "비교 기간",
        value=default_date_range(2),
        max_value=default_date_range(0)[1],
        key="cmp_range",
    )
    if not cmp_codes:
        st.info("ETF를 1개 이상 선택하세요.")
        st.stop()

    try:
        panel = fetch_close_panel(cmp_codes, cmp_start, cmp_end)
    except Exception as e:  # noqa: BLE001
        st.error(f"기간별 시세 조회 실패: {e}")
        st.stop()
    if panel.empty:
        st.info("선택한 기간의 데이터가 부족합니다.")
        st.stop()

    etfs = load_etf_list().set_index("code")
    panel = panel.dropna(how="all").ffill().dropna()
    normalized = panel / panel.iloc[0] * 100.0

    fig = go.Figure()
    for c in normalized.columns:
        name = etfs.loc[c, "name"] if c in etfs.index else c
        fig.add_trace(
            go.Scatter(
                x=normalized.index,
                y=normalized[c],
                mode="lines",
                name=f"{c} · {name}",
            )
        )
    fig.update_layout(
        height=460,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=10, b=10),
        yaxis_title="시작일=100 기준",
    )
    st.plotly_chart(fig, use_container_width=True)

    rows = []
    for c in panel.columns:
        m = summary_metrics(panel[c])
        rows.append(
            {
                "종목": f"{c} · {etfs.loc[c, 'name']}" if c in etfs.index else c,
                "총 수익률 (%)": round(m["total_return"] * 100, 2),
                "CAGR (%)": round(m["cagr"] * 100, 2),
                "변동성 (%)": round(m["volatility"] * 100, 2),
                "MDD (%)": round(m["max_drawdown"] * 100, 2),
                "샤프": round(m["sharpe"], 2),
            }
        )
    st.subheader("비교 지표")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
