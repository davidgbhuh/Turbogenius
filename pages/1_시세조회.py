"""ETF 시세 조회 & 차트 페이지."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from common import default_date_range, etf_selector, fetch_daily, require_client
from kis.quotes import get_current_price

st.set_page_config(page_title="시세 조회", page_icon="🕯", layout="wide")
client = require_client()

st.title("🕯 시세 조회 & 차트")

col_sel, col_range = st.columns([2, 3])
with col_sel:
    code = etf_selector("ETF 선택", default_codes=["069500"])
with col_range:
    default_start, default_end = default_date_range(1)
    start, end = st.date_input(
        "조회 기간", value=(default_start, default_end), max_value=default_end
    )

# 현재가
try:
    snap = get_current_price(client, code)
except Exception as e:  # noqa: BLE001
    st.error(f"현재가 조회 실패: {e}")
    st.stop()

m1, m2, m3, m4 = st.columns(4)
m1.metric("현재가", f"{snap['price']:,.0f} 원", f"{snap['change']:+,.0f} ({snap['change_pct']:+.2f}%)")
m2.metric("시가", f"{snap['open']:,.0f}")
m3.metric("고가 / 저가", f"{snap['high']:,.0f} / {snap['low']:,.0f}")
m4.metric("거래량", f"{snap['volume']:,.0f}")

# 차트
try:
    df = fetch_daily(code, start, end)
except Exception as e:  # noqa: BLE001
    st.error(f"기간별 시세 조회 실패: {e}")
    st.stop()
if df.empty:
    st.info("선택한 기간의 시세 데이터가 없습니다.")
    st.stop()

fig = go.Figure(
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
fig.update_layout(
    xaxis_rangeslider_visible=False,
    height=520,
    margin=dict(l=10, r=10, t=30, b=10),
    template="plotly_dark",
)
st.plotly_chart(fig, use_container_width=True)

with st.expander("일별 시세 데이터"):
    st.dataframe(df.iloc[::-1], use_container_width=True)
