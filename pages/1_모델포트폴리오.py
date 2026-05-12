"""모델 포트폴리오 페이지 — 분기별 비중 상세 + 변경 추적."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from analytics import aggregate_by_asset_class
from common import etf_asset_class_map, etf_name_map
from data import (
    PROFILE_SUMMARY,
    RISK_PROFILES,
    Quarter,
    current_quarter,
    get_model,
    get_note,
    list_quarters,
)

st.set_page_config(page_title="모델 포트폴리오", page_icon="🎯", layout="wide")

st.title("🎯 분기별 모델 포트폴리오")
st.caption("리스크 프로파일과 분기를 선택해 ETF 단위 목표 비중을 확인합니다.")

quarters = list_quarters()
names = etf_name_map()
asset_class = etf_asset_class_map()

default_q = current_quarter()
default_idx = quarters.index(default_q)

col_q, col_p = st.columns([2, 2])
with col_q:
    selected_q = st.selectbox(
        "분기 선택",
        quarters,
        index=default_idx,
        format_func=lambda q: f"{q.label()} ({q.short()})",
    )
with col_p:
    profile = st.radio("리스크 프로파일", RISK_PROFILES, horizontal=True, index=1)

info = PROFILE_SUMMARY[profile]
st.markdown(
    f"**{profile}** — {info['subtitle']}  ·  추천 연령대 {info['target_age']}  ·  "
    f"목표 수익률 {info['expected_return']}  ·  예상 MDD {info['expected_mdd']}"
)
note = get_note(selected_q)
if note:
    st.info(f"📌 {selected_q.label()} — {note}")

weights = get_model(selected_q, profile)

# ── 비중 표 ──────────────────────────────────────────────────────────────
rows = []
for code, w in sorted(weights.items(), key=lambda kv: -kv[1]):
    rows.append(
        {
            "코드": code,
            "종목명": names.get(code, code),
            "자산군": asset_class.get(code, "기타"),
            "비중": w,
        }
    )
df = pd.DataFrame(rows)
df_view = df.copy()
df_view["비중"] = df_view["비중"].map(lambda v: f"{v * 100:.1f}%")

left, right = st.columns([3, 2])
with left:
    st.subheader("종목별 비중")
    st.dataframe(df_view, use_container_width=True, hide_index=True)
with right:
    st.subheader("자산군 배분")
    agg = aggregate_by_asset_class(weights, asset_class)
    pie = go.Figure(
        data=[
            go.Pie(
                labels=list(agg.keys()),
                values=list(agg.values()),
                hole=0.45,
                sort=False,
            )
        ]
    )
    pie.update_traces(textinfo="label+percent")
    pie.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        template="plotly_dark",
        showlegend=False,
    )
    st.plotly_chart(pie, use_container_width=True)

st.divider()

# ── 분기 간 변경 추적 ────────────────────────────────────────────────────
st.subheader("분기 간 비중 변화")
prev_q: Quarter | None = next((q for q in reversed(quarters) if q < selected_q), None)
if prev_q is None:
    st.info("이전 분기 데이터가 없습니다. 두 번째 등록 분기부터 변화량이 표시됩니다.")
else:
    prev_w = get_model(prev_q, profile)
    all_codes = sorted(set(weights) | set(prev_w))
    diff_rows = []
    for code in all_codes:
        before = prev_w.get(code, 0.0)
        after = weights.get(code, 0.0)
        delta = after - before
        if abs(delta) < 1e-9:
            continue
        diff_rows.append(
            {
                "코드": code,
                "종목명": names.get(code, code),
                f"{prev_q.short()}": before,
                f"{selected_q.short()}": after,
                "변화": delta,
            }
        )
    if not diff_rows:
        st.success(f"{prev_q.label()} → {selected_q.label()} 사이 비중 변화 없음.")
    else:
        diff_df = pd.DataFrame(diff_rows).sort_values("변화", key=lambda s: s.abs(), ascending=False)
        bar = px.bar(
            diff_df,
            x="종목명",
            y="변화",
            color="변화",
            color_continuous_scale=["#ef4444", "#1f2937", "#22c55e"],
            range_color=[-diff_df["변화"].abs().max(), diff_df["변화"].abs().max()],
        )
        bar.update_layout(
            height=380,
            template="plotly_dark",
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_tickformat=".0%",
            yaxis_title="비중 변화 (%p)",
            xaxis_title="",
        )
        st.plotly_chart(bar, use_container_width=True)

        diff_view = diff_df.copy()
        for col in (f"{prev_q.short()}", f"{selected_q.short()}", "변화"):
            diff_view[col] = diff_view[col].map(lambda v: f"{v * 100:+.1f}%" if col == "변화" else f"{v * 100:.1f}%")
        st.dataframe(diff_view, use_container_width=True, hide_index=True)

st.divider()

# ── 분기 전체 비중 히트맵 ────────────────────────────────────────────────
st.subheader(f"{profile} — 분기별 비중 히트맵")
hm_codes = sorted({c for q in quarters for c in get_model(q, profile)})
matrix = []
for q in quarters:
    w = get_model(q, profile)
    matrix.append([w.get(c, 0.0) * 100 for c in hm_codes])
heat = go.Figure(
    data=go.Heatmap(
        z=matrix,
        x=[f"{names.get(c, c)}\n({c})" for c in hm_codes],
        y=[q.short() for q in quarters],
        colorscale="Blues",
        zmin=0,
        zmax=35,
        text=[[f"{v:.0f}" if v > 0 else "" for v in row] for row in matrix],
        texttemplate="%{text}",
        hovertemplate="%{y} · %{x}<br>비중: %{z:.1f}%<extra></extra>",
    )
)
heat.update_layout(
    height=max(260, 60 + len(quarters) * 38),
    template="plotly_dark",
    margin=dict(l=10, r=10, t=20, b=120),
    xaxis_tickangle=-30,
)
st.plotly_chart(heat, use_container_width=True)
