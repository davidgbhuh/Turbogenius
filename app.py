"""Turbogenius — 한국 주식 AI 분석기 + ETF 포트폴리오 대시보드 (Streamlit 메인 앱)."""

import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

def get_api_key_from_env() -> str:
    """Streamlit Cloud secrets 또는 .env 파일에서 API 키를 가져옵니다."""
    # Streamlit Cloud secrets 우선
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    # 로컬 .env 파일 또는 환경변수
    return os.getenv("ANTHROPIC_API_KEY", "")

from config import MARKETS, PERIODS
from data.stock_list import get_stock_list, search_stocks
from modules.data_fetcher import fetch_ohlcv, get_company_info
from modules.technical import add_all_indicators, get_indicator_summary
from modules.charts import candlestick_chart, rsi_chart, macd_chart, bollinger_chart
from modules.ai_analyst import generate_report

# ─── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Turbogenius | 주식 분석기",
    page_icon="📈",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card {
        background: #1e2130;
        border-radius: 10px;
        padding: 16px 20px;
        text-align: center;
    }
    .metric-label { color: #888; font-size: 0.85rem; margin-bottom: 4px; }
    .metric-value { color: #fafafa; font-size: 1.5rem; font-weight: 700; }
    .metric-delta-up { color: #FF3B30; font-size: 0.9rem; }
    .metric-delta-down { color: #007AFF; font-size: 0.9rem; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 Turbogenius")
    st.caption("한국 주식 AI 분석기")
    st.divider()

    # Market selection
    market = st.selectbox("시장", list(MARKETS.keys()))

    # Load stock list
    with st.spinner("종목 목록 로딩 중..."):
        stock_df = get_stock_list(market)

    # Search
    query = st.text_input("종목 검색 (이름 또는 코드)", placeholder="예: 삼성전자, 005930")
    filtered = search_stocks(stock_df, query)

    # 직접 코드 입력 (목록에 없는 종목도 조회 가능)
    direct_code = st.text_input(
        "종목 코드 직접 입력",
        placeholder="예: 001440  (대한전선)",
        help="6자리 종목 코드를 입력하면 목록에 없는 종목도 바로 조회됩니다.",
    )

    # 선택 우선순위: 직접 입력 > 검색 결과
    selected_ticker = None
    selected_name = None

    if direct_code.strip():
        selected_ticker = direct_code.strip().zfill(6)
        match = stock_df[stock_df["ticker"] == selected_ticker]
        selected_name = match.iloc[0]["name"] if not match.empty else selected_ticker
    elif not filtered.empty:
        options = [f"{row['ticker']} | {row['name']}" for _, row in filtered.iterrows()]
        selected = st.selectbox("종목 선택", options)
        selected_ticker = selected.split(" | ")[0]
        selected_name = selected.split(" | ")[1]
    else:
        if query:
            st.warning(f"'{query}' 검색 결과가 없습니다. 위 코드 직접 입력창을 이용하세요.")

    # Period
    period_label = st.selectbox("조회 기간", list(PERIODS.keys()), index=3)
    period_value = PERIODS[period_label]

    st.divider()

    # API key (Streamlit Cloud secrets 또는 직접 입력)
    env_key = get_api_key_from_env()
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=env_key,
        help="AI 분석 리포트 생성에 필요합니다. Streamlit Cloud 배포 시 Secrets에 설정하면 자동 입력됩니다.",
    )

# ─── Main area ───────────────────────────────────────────────────────────────
if not selected_ticker:
    st.info("왼쪽 사이드바에서 종목을 검색하거나 코드를 직접 입력하세요.\n\n예) 대한전선 → 코드 직접 입력에 `001440` 입력")
    st.stop()

st.header(f"{selected_name} ({selected_ticker})")

# Load data
with st.spinner("데이터 로딩 중..."):
    df_raw = fetch_ohlcv(selected_ticker, market, period_value)

if df_raw.empty:
    st.error("주가 데이터를 불러올 수 없습니다. 종목 코드와 네트워크를 확인해주세요.")
    st.stop()

df = add_all_indicators(df_raw)
summary = get_indicator_summary(df)

# ── Metric cards ──────────────────────────────────────────────────────────────
current_price = summary["close"]
prev_close = df["Close"].iloc[-2] if len(df) > 1 else current_price
delta = current_price - prev_close
delta_pct = (delta / prev_close * 100) if prev_close else 0
delta_class = "metric-delta-up" if delta >= 0 else "metric-delta-down"
delta_sign = "▲" if delta >= 0 else "▼"

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">현재가</div>
        <div class="metric-value">{current_price:,.0f}원</div>
        <div class="{delta_class}">{delta_sign} {abs(delta):,.0f} ({abs(delta_pct):.2f}%)</div>
    </div>""", unsafe_allow_html=True)

with col2:
    rsi_val = summary.get("RSI")
    rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">RSI (14)</div>
        <div class="metric-value">{rsi_str}</div>
    </div>""", unsafe_allow_html=True)

with col3:
    vol = summary.get("volume", 0)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">거래량</div>
        <div class="metric-value">{vol:,.0f}</div>
    </div>""", unsafe_allow_html=True)

with col4:
    ma20 = summary.get("MA20")
    ma20_str = f"{ma20:,.0f}원" if ma20 else "N/A"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">20일 이동평균</div>
        <div class="metric-value">{ma20_str}</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📈 가격 차트", "📊 기술적 분석", "🤖 AI 분석", "ℹ️ 기업 정보"])

with tab1:
    st.plotly_chart(candlestick_chart(df, selected_name), use_container_width=True)

with tab2:
    st.plotly_chart(bollinger_chart(df), use_container_width=True)
    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(rsi_chart(df), use_container_width=True)
    with col_r:
        st.plotly_chart(macd_chart(df), use_container_width=True)

with tab3:
    st.subheader("AI 주식 분석 리포트")

    # 종목이 바뀌면 이전 리포트 초기화
    if st.session_state.get("report_ticker") != selected_ticker:
        st.session_state["ai_report"] = ""
        st.session_state["report_ticker"] = selected_ticker

    if not api_key:
        st.info("사이드바에 Anthropic API Key를 입력하면 AI 분석 리포트를 생성할 수 있습니다.")
    else:
        if st.button("AI 분석 리포트 생성", type="primary"):
            with st.spinner(f"{selected_name} 분석 리포트를 생성하는 중입니다..."):
                try:
                    info = get_company_info(selected_ticker, market)
                    report = generate_report(info, summary, period_label, api_key)
                    st.session_state["ai_report"] = report
                    st.session_state["ai_error"] = ""
                except Exception as e:
                    st.session_state["ai_report"] = ""
                    st.session_state["ai_error"] = str(e)

        if st.session_state.get("ai_error"):
            st.error(f"리포트 생성 중 오류가 발생했습니다: {st.session_state['ai_error']}")
        elif st.session_state.get("ai_report"):
            st.markdown(st.session_state["ai_report"])

with tab4:
    with st.spinner("기업 정보 로딩 중..."):
        info = get_company_info(selected_ticker, market)

    st.subheader(info.get("name", selected_name))

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("섹터", info.get("sector", "-"))
        mc = info.get("market_cap")
        st.metric("시가총액", f"{mc / 1e12:.2f}조 원" if mc else "N/A")
        st.metric("PER", f"{info.get('per', 'N/A'):.1f}배" if info.get("per") else "N/A")
    with col_b:
        st.metric("업종", info.get("industry", "-"))
        emp = info.get("employees")
        st.metric("직원 수", f"{emp:,}명" if emp else "N/A")
        st.metric("PBR", f"{info.get('pbr', 'N/A'):.2f}배" if info.get("pbr") else "N/A")

    desc = info.get("description", "")
    if desc:
        st.divider()
        st.caption("기업 개요")
        st.write(desc)

    website = info.get("website", "")
    if website:
        st.link_button("공식 웹사이트", website)
