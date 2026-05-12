"""포트폴리오 백테스트 페이지."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import portfolio_metrics, portfolio_value
from common import (
    default_date_range,
    etf_selector,
    fetch_close_panel,
    load_etf_list,
    require_client,
)

st.set_page_config(page_title="포트폴리오", page_icon="🧺", layout="wide")
require_client()

st.title("🧺 포트폴리오 백테스트")
st.caption("ETF를 선택하고 비중을 설정하면 시작일 기준 매수·보유 시 가치 추이를 보여줍니다.")

codes = etf_selector(
    "ETF 선택 (복수)", default_codes=["069500", "133690"], multi=True, key="port_codes"
)
default_start, default_end = default_date_range(3)
col_range, col_init = st.columns([3, 1])
with col_range:
    start, end = st.date_input(
        "조회 기간", value=(default_start, default_end), max_value=default_end
    )
with col_init:
    initial = st.number_input("초기 자본 (원)", 100_000, 1_000_000_000, 1_000_000, 100_000)

if not codes:
    st.info("ETF를 1개 이상 선택하세요.")
    st.stop()

etfs = load_etf_list().set_index("code")
st.subheader("비중 설정")
weights: dict[str, float] = {}
cols = st.columns(min(len(codes), 4))
for i, code in enumerate(codes):
    with cols[i % len(cols)]:
        name = etfs.loc[code, "name"] if code in etfs.index else code
        weights[code] = st.slider(
            f"{code} · {name}", 0.0, 1.0, round(1.0 / len(codes), 2), 0.05, key=f"w_{code}"
        )

total_w = sum(weights.values())
if total_w == 0:
    st.warning("총 비중이 0입니다.")
    st.stop()
st.caption(f"비중 합계: {total_w:.2f} (자동 정규화됩니다)")

try:
    panel = fetch_close_panel(codes, start, end)
except Exception as e:  # noqa: BLE001
    st.error(f"기간별 시세 조회 실패: {e}")
    st.stop()
if panel.empty:
    st.info("선택한 기간의 데이터가 부족합니다.")
    st.stop()

value = portfolio_value(panel, weights, initial=initial)
if value.empty:
    st.info("포트폴리오 값을 계산할 수 없습니다.")
    st.stop()

metrics = portfolio_metrics(value)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("총 수익률", f"{metrics['total_return'] * 100:+.2f}%")
m2.metric("CAGR", f"{metrics['cagr'] * 100:+.2f}%")
m3.metric("변동성", f"{metrics['volatility'] * 100:.2f}%")
m4.metric("MDD", f"{metrics['max_drawdown'] * 100:.2f}%")
m5.metric("샤프", f"{metrics['sharpe']:.2f}")

st.subheader("포트폴리오 가치 추이")
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=value.index,
        y=value.values,
        mode="lines",
        line=dict(color="#22c55e", width=2),
        name="포트폴리오 가치",
    )
)
fig.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=30, b=10),
    template="plotly_dark",
    yaxis_title="원",
)
st.plotly_chart(fig, use_container_width=True)

# 종목별 비중 파이
norm = {c: w / total_w for c, w in weights.items() if w > 0}
if norm:
    st.subheader("비중 분포")
    pie = go.Figure(
        data=[
            go.Pie(
                labels=[f"{c} · {etfs.loc[c, 'name']}" if c in etfs.index else c for c in norm],
                values=list(norm.values()),
                hole=0.4,
            )
        ]
    )
    pie.update_layout(height=360, template="plotly_dark", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(pie, use_container_width=True)

with st.expander("일별 포트폴리오 가치"):
    st.dataframe(
        pd.DataFrame({"value": value}).iloc[::-1],
        use_container_width=True,
    )
