"""내 포트폴리오 — 보유 종목 입력 + 목표 대비 드리프트 + 리밸런싱 매매 권고."""
from __future__ import annotations

from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import aggregate_by_asset_class, build_rebalance_table
from common import etf_asset_class_map, etf_name_map, fetch_daily, require_client
from data import (
    PROFILE_SUMMARY,
    RISK_PROFILES,
    Quarter,
    current_quarter,
    get_model,
    list_quarters,
)
from kis.quotes import get_current_price

st.set_page_config(page_title="내 포트폴리오", page_icon="📂", layout="wide")
client = require_client()

st.title("📂 내 포트폴리오 — 드리프트 & 리밸런싱")
st.caption(
    "현재 보유 ETF 수량을 입력하면 선택한 모델과 비교한 드리프트와 매매 권고가 자동 계산됩니다."
)

names = etf_name_map()
asset_class = etf_asset_class_map()
quarters = list_quarters()
default_q = current_quarter()

c1, c2, c3 = st.columns([2, 2, 2])
with c1:
    profile = st.selectbox("목표 리스크 프로파일", RISK_PROFILES, index=1)
with c2:
    target_q: Quarter = st.selectbox(
        "기준 분기",
        quarters,
        index=quarters.index(default_q),
        format_func=lambda q: q.short(),
    )
with c3:
    extra_cash = st.number_input(
        "추가 입금 (선택, 원)", min_value=0, value=0, step=100_000
    )

info = PROFILE_SUMMARY[profile]
st.markdown(
    f"**기준 모델**: {profile} · {info['subtitle']}  ·  목표 {info['expected_return']}"
)

target = get_model(target_q, profile)
target_codes = list(target)

# ── 보유 수량 입력 ───────────────────────────────────────────────────────
st.subheader("보유 수량 입력")
st.caption("모델 종목과 그 외 추가 보유 종목을 입력하세요. 0 인 행은 무시됩니다.")

if "holdings_table" not in st.session_state:
    st.session_state.holdings_table = pd.DataFrame(
        [
            {"코드": code, "종목명": names.get(code, code), "보유수량": 0}
            for code in target_codes
        ]
    )
else:
    cur = st.session_state.holdings_table.set_index("코드")
    for code in target_codes:
        if code not in cur.index:
            cur.loc[code] = [names.get(code, code), 0]
    st.session_state.holdings_table = cur.reset_index()[["코드", "종목명", "보유수량"]]

edited = st.data_editor(
    st.session_state.holdings_table,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "코드": st.column_config.TextColumn("ETF 코드", help="6자리 종목코드", required=True),
        "종목명": st.column_config.TextColumn("종목명", disabled=False),
        "보유수량": st.column_config.NumberColumn("보유수량", min_value=0, step=1),
    },
    key="holdings_editor",
)
st.session_state.holdings_table = edited

holdings: dict[str, float] = {}
for _, row in edited.iterrows():
    code = str(row.get("코드", "")).strip()
    qty = float(row.get("보유수량", 0) or 0)
    if not code or qty <= 0:
        continue
    holdings[code] = holdings.get(code, 0.0) + qty

all_codes = sorted(set(holdings) | set(target))
if not all_codes:
    st.info("보유 수량을 입력하면 분석이 시작됩니다.")
    st.stop()

# ── 현재가 조회 ──────────────────────────────────────────────────────────
prices: dict[str, float] = {}
miss: list[str] = []
with st.spinner("KIS 현재가 조회 중..."):
    for code in all_codes:
        try:
            snap = get_current_price(client, code)
            prices[code] = snap["price"] or snap["prev_close"]
        except Exception as e:  # noqa: BLE001
            miss.append(f"{code} ({e})")

if miss:
    st.warning("현재가 조회 실패: " + ", ".join(miss))

# ── 리밸런싱 표 ──────────────────────────────────────────────────────────
table = build_rebalance_table(
    holdings=holdings,
    prices=prices,
    target_weights=target,
    names={c: names.get(c, c) for c in all_codes},
    extra_cash=extra_cash,
)
if table.empty:
    st.error("총 평가금액이 0 입니다.")
    st.stop()

total_value = float((table["current_value"]).sum()) + float(extra_cash)
total_drift = float(table["delta_weight"].abs().sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("총 평가금액", f"{int(total_value - extra_cash):,} 원")
m2.metric("추가 입금", f"{int(extra_cash):,} 원")
m3.metric("리밸런싱 후 합계", f"{int(total_value):,} 원")
m4.metric(
    "총 드리프트",
    f"{total_drift * 100:.1f}%p",
    help="목표 대비 종목별 비중 차이의 절댓값 합 — 5%p 이상이면 리밸런싱 권장",
)

# ── 드리프트 차트 ────────────────────────────────────────────────────────
st.subheader("종목별 드리프트")
plot_df = table.copy()
plot_df["라벨"] = plot_df["code"] + " · " + plot_df["name"]
fig = px.bar(
    plot_df,
    x="라벨",
    y=plot_df["delta_weight"] * 100,
    color=plot_df["delta_weight"] * 100,
    color_continuous_scale=["#22c55e", "#1f2937", "#ef4444"],
    range_color=[
        -max(plot_df["delta_weight"].abs().max() * 100, 1),
        max(plot_df["delta_weight"].abs().max() * 100, 1),
    ],
)
fig.update_layout(
    height=380,
    template="plotly_dark",
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title="현재 - 목표 비중 (%p)",
    xaxis_title="",
)
st.plotly_chart(fig, use_container_width=True)

# ── 매매 권고 표 ─────────────────────────────────────────────────────────
st.subheader("리밸런싱 매매 권고")
view = pd.DataFrame(
    {
        "코드": table["code"],
        "종목명": table["name"],
        "현재가 (원)": table["current_price"].map(lambda v: f"{int(v):,}"),
        "보유수량": table["current_shares"].map(lambda v: f"{int(v):,}"),
        "현재 평가금": table["current_value"].map(lambda v: f"{int(v):,}"),
        "현재 비중": (table["current_weight"] * 100).map(lambda v: f"{v:.1f}%"),
        "목표 비중": (table["target_weight"] * 100).map(lambda v: f"{v:.1f}%"),
        "드리프트": (table["delta_weight"] * 100).map(lambda v: f"{v:+.1f}%p"),
        "필요 매매": table["delta_value"].map(
            lambda v: f"매수 {int(v):,}원" if v > 0 else (f"매도 {int(-v):,}원" if v < 0 else "—")
        ),
        "권장 수량": table["suggested_trade_shares"].map(
            lambda v: f"매수 {int(v):,}주" if v > 0.5 else (f"매도 {int(-v):,}주" if v < -0.5 else "—")
        ),
    }
)
st.dataframe(view, use_container_width=True, hide_index=True)

# ── 자산군 단위 요약 ─────────────────────────────────────────────────────
st.subheader("자산군 배분 — 현재 vs 목표")
current_weights = dict(zip(table["code"], table["current_weight"]))
cur_agg = aggregate_by_asset_class(current_weights, asset_class)
tgt_agg = aggregate_by_asset_class(target, asset_class)
classes = sorted(set(cur_agg) | set(tgt_agg))
asset_df = pd.DataFrame(
    [
        {
            "자산군": cls,
            "구분": kind,
            "비중": (cur_agg if kind == "현재" else tgt_agg).get(cls, 0.0) * 100,
        }
        for cls in classes
        for kind in ("현재", "목표")
    ]
)
fig2 = px.bar(
    asset_df,
    x="자산군",
    y="비중",
    color="구분",
    barmode="group",
    text=asset_df["비중"].map(lambda v: f"{v:.0f}%"),
)
fig2.update_layout(
    height=340,
    template="plotly_dark",
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title="비중 (%)",
)
fig2.update_traces(textposition="outside")
st.plotly_chart(fig2, use_container_width=True)

st.caption(
    f"⏱ 마지막 조회: {date.today().isoformat()} · 현재가는 KIS 실시간 시세 기준. "
    "분기 첫 영업일 또는 드리프트 5%p 이상 시 리밸런싱을 권장합니다."
)
