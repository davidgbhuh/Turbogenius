"""개인연금 ETF 포트폴리오 대시보드 — 메인 페이지.

- 현재 분기의 모델 포트폴리오 요약
- 3가지 리스크 모델(안정/균형/성장) 자산군 배분
- 분기별 변경 히스토리 진입점

분기별 모델 사전은 ``data/portfolios.py`` 의 ``QUARTERLY_MODELS`` 에서 관리합니다.
새 분기를 추가하려면 해당 dict 에 ``(year, quarter)`` 항목을 채워 넣고 push 하세요.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics import aggregate_by_asset_class
from common import (
    etf_asset_class_map,
    etf_name_map,
    get_client,
    load_etf_list,
)
from data import (
    PROFILE_SUMMARY,
    RISK_PROFILES,
    current_quarter,
    get_model,
    get_note,
    list_quarters,
    validate_all,
)

st.set_page_config(
    page_title="개인연금 ETF Dashboard",
    page_icon="💼",
    layout="wide",
)

st.title("💼 개인연금 ETF 포트폴리오 대시보드")
st.caption(
    "한국투자증권 OpenAPI 기반 · 분기별 리밸런싱 모델 · 안정/균형/성장 3종 리스크 프로파일"
)

# ── KIS 자격증명 상태 배너 ────────────────────────────────────────────────
client = get_client()
if client is None:
    st.warning(
        "KIS API 자격증명이 설정되지 않았습니다. 시세·수익률 페이지는 비활성화됩니다.\n\n"
        "- **로컬 실행**: 루트의 `.env.example` 을 복사해 `.env` 를 만들고 `KIS_APP_KEY`, `KIS_APP_SECRET` 입력\n"
        "- **Streamlit Cloud**: 앱 설정 → **Secrets** 에 동일한 키 입력"
    )
    err = st.session_state.get("_kis_error")
    if err:
        with st.expander("오류 상세"):
            st.code(err)

# ── 무결성 체크 ───────────────────────────────────────────────────────────
errors = validate_all()
if errors:
    st.error("⚠️ 모델 포트폴리오 비중 합계 오류:\n\n" + "\n".join(f"- {e}" for e in errors))

# ── 현재 분기 헤더 ────────────────────────────────────────────────────────
quarters = list_quarters()
this_q = current_quarter()
prev_q = next((q for q in reversed(quarters) if q < this_q), None)

col1, col2, col3 = st.columns([2, 2, 2])
with col1:
    st.metric("현재 운용 분기", this_q.label())
with col2:
    next_review = (this_q.q % 4) + 1
    next_year = this_q.year + (1 if this_q.q == 4 else 0)
    st.metric("다음 리밸런싱 시점", f"{next_year}년 {next_review}분기 첫 영업일")
with col3:
    st.metric("등록된 분기 수", f"{len(quarters)}개")

note = get_note(this_q)
if note:
    st.info(f"📌 **{this_q.label()} 운용 코멘트** — {note}")

st.divider()

# ── 리스크 프로파일 카드 ──────────────────────────────────────────────────
st.subheader("리스크 프로파일별 모델 포트폴리오")

names = etf_name_map()
asset_class = etf_asset_class_map()

prof_cols = st.columns(3)
for i, profile in enumerate(RISK_PROFILES):
    info = PROFILE_SUMMARY[profile]
    weights = get_model(this_q, profile)
    agg = aggregate_by_asset_class(weights, asset_class)
    with prof_cols[i]:
        st.markdown(f"### {profile}")
        st.caption(info["subtitle"])
        st.markdown(
            f"- **추천 연령대**: {info['target_age']}\n"
            f"- **목표 수익률**: {info['expected_return']}\n"
            f"- **예상 MDD**: {info['expected_mdd']}"
        )
        st.write(info["description"])

        agg_df = pd.DataFrame(
            sorted(agg.items(), key=lambda x: -x[1]),
            columns=["자산군", "비중"],
        )
        agg_df["비중"] = agg_df["비중"].map(lambda v: f"{v * 100:.1f}%")
        st.dataframe(agg_df, use_container_width=True, hide_index=True)

st.divider()

# ── 전체 보유 비중 비교 ───────────────────────────────────────────────────
st.subheader("자산군 배분 비교")

rows = []
for profile in RISK_PROFILES:
    weights = get_model(this_q, profile)
    agg = aggregate_by_asset_class(weights, asset_class)
    for cls, w in agg.items():
        rows.append({"리스크 프로파일": profile, "자산군": cls, "비중": w * 100})
agg_df = pd.DataFrame(rows)

fig = px.bar(
    agg_df,
    x="리스크 프로파일",
    y="비중",
    color="자산군",
    text=agg_df["비중"].map(lambda v: f"{v:.0f}%"),
    category_orders={
        "리스크 프로파일": list(RISK_PROFILES),
        "자산군": ["국내주식", "선진국주식", "신흥국주식", "국내채권", "해외채권", "대체자산"],
    },
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_layout(
    height=420,
    template="plotly_dark",
    margin=dict(l=10, r=10, t=10, b=10),
    yaxis_title="비중 (%)",
    barmode="stack",
)
fig.update_traces(textposition="inside")
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── 페이지 안내 ───────────────────────────────────────────────────────────
st.subheader("페이지 안내")
st.markdown(
    """
| 페이지 | 용도 |
| --- | --- |
| **🎯 모델 포트폴리오** | 분기별 모델 비중 상세, 종목 단위 변화 |
| **📂 내 포트폴리오** | 보유 종목 입력 → 목표 대비 드리프트 + 리밸런싱 매매 권고 |
| **📊 분기 성과 리뷰** | 모델 포트폴리오 수익률, KOSPI200·S&P500 벤치마크 비교 |
| **🔎 ETF 분석** | 개별 ETF 시세·캔들·수익률·MDD |
"""
)

with st.expander("💡 분기별 모델 업데이트 방법"):
    st.markdown(
        """
        1. `data/portfolios.py` 파일을 엽니다.
        2. `QUARTERLY_MODELS` dict 하단에 새 분기 키 (예: `(2026, 3)`) 를 추가합니다.
        3. 세 가지 모델(안정형 / 균형형 / 성장형) 각각의 종목 비중을 채웁니다.
           - 비중 합계가 정확히 **1.0** 이어야 합니다.
           - 코드는 `data/etf_list.csv` 에 있어야 합니다.
        4. `NOTES` dict 에 운용 코멘트를 남깁니다.
        5. `git commit` & `git push` — 대시보드가 자동으로 새 분기를 인식합니다.
        """
    )

with st.expander("📋 등록된 ETF 유니버스"):
    st.dataframe(load_etf_list(), use_container_width=True, hide_index=True)

if prev_q:
    st.caption(
        f"이전 분기: {prev_q.label()} — 좌측 사이드바의 **모델 포트폴리오** 페이지에서 분기 간 변경을 확인하세요."
    )
