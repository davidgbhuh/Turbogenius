"""ETF 수익률·리스크 분석 페이지."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from analytics import cumulative_returns, summary_metrics
from common import default_date_range, etf_selector, fetch_daily, require_client

st.set_page_config(page_title="수익률 분석", page_icon="📊", layout="wide")
require_client()

st.title("📊 수익률 분석")

col_sel, col_range, col_rf = st.columns([2, 3, 1])
with col_sel:
    code = etf_selector("ETF 선택", default_codes=["069500"])
with col_range:
    default_start, default_end = default_date_range(3)
    start, end = st.date_input(
        "조회 기간", value=(default_start, default_end), max_value=default_end
    )
with col_rf:
    risk_free = st.number_input("무위험 수익률", 0.0, 0.2, 0.03, 0.005, format="%.3f")

try:
    df = fetch_daily(code, start, end)
except Exception as e:  # noqa: BLE001
    st.error(f"기간별 시세 조회 실패: {e}")
    st.stop()
if df.empty or len(df) < 2:
    st.info("선택한 기간의 데이터가 부족합니다.")
    st.stop()

prices = df["close"]
metrics = summary_metrics(prices, risk_free=risk_free)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("총 수익률", f"{metrics['total_return'] * 100:+.2f}%")
m2.metric("연환산(CAGR)", f"{metrics['cagr'] * 100:+.2f}%")
m3.metric("변동성(연)", f"{metrics['volatility'] * 100:.2f}%")
m4.metric("최대낙폭(MDD)", f"{metrics['max_drawdown'] * 100:.2f}%")
m5.metric("샤프", f"{metrics['sharpe']:.2f}")

# 누적 수익률
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
    height=400,
    margin=dict(l=10, r=10, t=30, b=10),
    template="plotly_dark",
    yaxis_title="%",
)
st.plotly_chart(fig, use_container_width=True)

# Drawdown
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
    height=260,
    margin=dict(l=10, r=10, t=30, b=10),
    template="plotly_dark",
    yaxis_title="Drawdown (%)",
)
st.subheader("Drawdown")
st.plotly_chart(fig_dd, use_container_width=True)
