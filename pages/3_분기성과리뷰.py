"""분기 성과 리뷰 — 모델 포트폴리오 수익률, 벤치마크(KOSPI200·S&P500) 비교."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from analytics import portfolio_metrics, portfolio_value
from common import etf_name_map, fetch_close_panel, require_client
from data import (
    PROFILE_SUMMARY,
    RISK_PROFILES,
    Quarter,
    current_quarter,
    get_model,
    list_quarters,
)

st.set_page_config(page_title="분기 성과 리뷰", page_icon="📊", layout="wide")
require_client()

st.title("📊 분기 성과 리뷰")
st.caption(
    "선택한 분기에 모델 비중을 매수·보유했다고 가정한 가상 포트폴리오의 누적 수익률과 "
    "주요 벤치마크를 비교합니다."
)

BENCHMARKS: dict[str, str] = {
    "069500": "KOSPI200 (KODEX 200)",
    "360750": "S&P500 (TIGER 미국S&P500)",
    "152380": "국고채 10년 (KODEX 국고채10년)",
}

names = etf_name_map()
quarters = list_quarters()
default_q = current_quarter()

c1, c2, c3 = st.columns([2, 2, 3])
with c1:
    start_q: Quarter = st.selectbox(
        "기준 분기 (매수 시점)",
        quarters,
        index=0,
        format_func=lambda q: q.short(),
    )
with c2:
    profile = st.selectbox("리스크 프로파일", RISK_PROFILES, index=1)
with c3:
    end_date = st.date_input(
        "종료일", value=date.today(), max_value=date.today()
    )

info = PROFILE_SUMMARY[profile]
st.markdown(
    f"**{profile}** · {info['subtitle']}  ·  목표 {info['expected_return']}  ·  "
    f"예상 MDD {info['expected_mdd']}"
)

start_date = start_q.start_date()
if start_date >= end_date:
    st.error("종료일이 시작 분기 이후여야 합니다.")
    st.stop()

target = get_model(start_q, profile)
codes = list(target.keys())
benchmark_codes = list(BENCHMARKS.keys())
all_codes = list(dict.fromkeys(codes + benchmark_codes))

with st.spinner("KIS 시세 조회 중..."):
    try:
        panel = fetch_close_panel(all_codes, start_date, end_date)
    except Exception as e:  # noqa: BLE001
        st.error(f"시세 조회 실패: {e}")
        st.stop()

if panel.empty:
    st.info("조회된 가격 데이터가 부족합니다.")
    st.stop()

# ── 모델 포트폴리오 가치 시계열 ──────────────────────────────────────────
INITIAL = 10_000_000  # 1천만원
pf_value = portfolio_value(panel[[c for c in codes if c in panel.columns]], target, initial=INITIAL)
if pf_value.empty:
    st.warning("모델 포트폴리오 가격 데이터가 부족합니다.")
    st.stop()
pf_norm = pf_value / pf_value.iloc[0] * 100

# ── 벤치마크 정규화 ──────────────────────────────────────────────────────
bench_series: dict[str, pd.Series] = {}
for code in benchmark_codes:
    if code not in panel.columns:
        continue
    s = panel[code].dropna()
    if s.empty:
        continue
    bench_series[code] = s / s.iloc[0] * 100

# ── 차트 ─────────────────────────────────────────────────────────────────
fig = go.Figure()
fig.add_trace(
    go.Scatter(
        x=pf_norm.index,
        y=pf_norm.values,
        mode="lines",
        name=f"{profile} 모델",
        line=dict(color="#22c55e", width=2.5),
    )
)
colors = {"069500": "#3b82f6", "360750": "#f59e0b", "152380": "#a78bfa"}
for code, series in bench_series.items():
    fig.add_trace(
        go.Scatter(
            x=series.index,
            y=series.values,
            mode="lines",
            name=BENCHMARKS[code],
            line=dict(color=colors.get(code, "#94a3b8"), width=1.5, dash="dot"),
        )
    )
fig.update_layout(
    height=460,
    template="plotly_dark",
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title=f"{start_q.short()} 시작 = 100",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig, use_container_width=True)

# ── 지표 표 ──────────────────────────────────────────────────────────────
st.subheader("지표 비교")
rows: list[dict] = []
pf_metrics = portfolio_metrics(pf_value)
rows.append({"종목/포트폴리오": f"{profile} 모델", **pf_metrics})
for code, series in bench_series.items():
    s = panel[code].dropna()
    rows.append({"종목/포트폴리오": BENCHMARKS[code], **portfolio_metrics(s)})

view = pd.DataFrame(
    {
        "종목/포트폴리오": [r["종목/포트폴리오"] for r in rows],
        "총 수익률": [f"{r['total_return'] * 100:+.2f}%" for r in rows],
        "CAGR": [f"{r['cagr'] * 100:+.2f}%" for r in rows],
        "변동성(연)": [f"{r['volatility'] * 100:.2f}%" for r in rows],
        "MDD": [f"{r['max_drawdown'] * 100:.2f}%" for r in rows],
        "샤프": [f"{r['sharpe']:.2f}" for r in rows],
    }
)
st.dataframe(view, use_container_width=True, hide_index=True)

# ── 종목별 누적 기여도 ───────────────────────────────────────────────────
st.subheader("종목별 누적 기여도")
contrib_rows = []
panel_codes = [c for c in codes if c in panel.columns]
slice_panel = panel[panel_codes].dropna(how="all").ffill().dropna()
if not slice_panel.empty:
    first = slice_panel.iloc[0]
    last = slice_panel.iloc[-1]
    for code in panel_codes:
        if first[code] <= 0:
            continue
        ret = float(last[code] / first[code] - 1.0)
        w = target.get(code, 0.0)
        contrib_rows.append(
            {
                "종목": f"{code} · {names.get(code, code)}",
                "비중": f"{w * 100:.1f}%",
                "기간 수익률": f"{ret * 100:+.2f}%",
                "기여도 (비중×수익률)": f"{w * ret * 100:+.2f}%p",
                "_sort": w * ret,
            }
        )
    contrib_df = pd.DataFrame(contrib_rows).sort_values("_sort", ascending=False).drop(columns="_sort")
    st.dataframe(contrib_df, use_container_width=True, hide_index=True)
else:
    st.info("종목별 기여도를 계산할 데이터가 부족합니다.")

st.caption(
    f"📌 {start_q.label()} 첫 영업일 ~ {end_date.isoformat()} · "
    f"초기 자본 {INITIAL:,}원 · 매수 후 보유(buy & hold) 가정."
)
