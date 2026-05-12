"""KIS API 기반 ETF Dashboard — 진입점."""
from __future__ import annotations

import streamlit as st

from common import get_client, load_etf_list

st.set_page_config(page_title="KIS ETF Dashboard", page_icon="📈", layout="wide")

st.title("📈 KIS ETF Dashboard")
st.caption("한국투자증권 OpenAPI를 사용한 국내 ETF 시세·수익률 분석 도구")

client = get_client()
if client is None:
    st.warning(
        "KIS API 자격증명이 설정되지 않았습니다.\n\n"
        "- **로컬 실행**: 루트의 `.env.example` 을 복사해 `.env` 를 만들고 `KIS_APP_KEY`, `KIS_APP_SECRET` 입력\n"
        "- **Streamlit Cloud**: 앱 대시보드 → ⋮ → **Settings → Secrets** 에 동일한 키를 TOML 형식으로 입력"
    )
    err = st.session_state.get("_kis_error")
    if err:
        st.code(err)
else:
    st.success("KIS API 연결 준비 완료 — 좌측 사이드바에서 페이지를 선택하세요.")

st.markdown(
    """
    ### 페이지 안내
    - **시세 조회 & 차트** — ETF 현재가, 일/주/월 OHLCV 차트
    - **수익률 분석** — 누적 수익률, CAGR, MDD, 변동성, 샤프
    - **포트폴리오** — 여러 ETF를 비중으로 묶어 백테스트
    - **ETF 비교** — 정규화 수익률 라인으로 동시 비교
    """
)

with st.expander("ETF 종목 리스트", expanded=False):
    st.dataframe(load_etf_list(), use_container_width=True, hide_index=True)
