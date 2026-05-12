"""여러 ETF의 정규화 수익률 비교 페이지."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import summary_metrics
from common import (
    default_date_range,
    etf_selector,
    fetch_close_panel,
    load_etf_list,
    require_client,
)

st.set_page_config(page_title="ETF 비교", page_icon="⚖️", layout="wide")
require_client()

st.title("⚖️ ETF 간 비교")

codes = etf_selector(
    "비교할 ETF 선택", default_codes=["069500", "133690", "360750"], multi=True, key="cmp_codes"
)
default_start, default_end = default_date_range(2)
start, end = st.date_input(
    "조회 기간", value=(default_start, default_end), max_value=default_end
)

if len(codes) < 1:
    st.info("ETF를 1개 이상 선택하세요.")
    st.stop()

panel = fetch_close_panel(codes, start, end)
if panel.empty:
    st.info("선택한 기간의 데이터가 부족합니다.")
    st.stop()

etfs = load_etf_list().set_index("code")
panel = panel.dropna(how="all").ffill().dropna()
normalized = panel / panel.iloc[0] * 100.0

fig = go.Figure()
for code in normalized.columns:
    name = etfs.loc[code, "name"] if code in etfs.index else code
    fig.add_trace(
        go.Scatter(
            x=normalized.index,
            y=normalized[code],
            mode="lines",
            name=f"{code} · {name}",
        )
    )
fig.update_layout(
    height=480,
    margin=dict(l=10, r=10, t=30, b=10),
    template="plotly_dark",
    yaxis_title="시작일=100 기준",
)
st.plotly_chart(fig, use_container_width=True)

# 메트릭 테이블
rows = []
for code in panel.columns:
    metrics = summary_metrics(panel[code])
    rows.append(
        {
            "종목": f"{code} · {etfs.loc[code, 'name']}" if code in etfs.index else code,
            "총 수익률 (%)": round(metrics["total_return"] * 100, 2),
            "CAGR (%)": round(metrics["cagr"] * 100, 2),
            "변동성 (%)": round(metrics["volatility"] * 100, 2),
            "MDD (%)": round(metrics["max_drawdown"] * 100, 2),
            "샤프": round(metrics["sharpe"], 2),
        }
    )
st.subheader("비교 지표")
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
