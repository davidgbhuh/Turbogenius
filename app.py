"""Turbogenius — ETF 글로벌 트렌드 포트폴리오 대시보드."""

import json
import os
import urllib.parse
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from modules.github_storage import load_from_github, save_to_github, is_configured
from modules.kis_api import (
    is_configured as kis_is_configured,
    get_investor_flow,
    get_etf_components,
    get_etf_nav_trend,
    get_current_price,
)

load_dotenv()

# ── 공통 유틸 ─────────────────────────────────────────────────────────────────

HISTORY_PATH = Path(__file__).parent / "data" / "etf_portfolio_history.json"
ACTION_COLOR = {
    "증가": "#FF3B30", "신규 편입": "#FF3B30",
    "감소": "#007AFF", "제거": "#888888",
    "유지": "#34C759",
}
PERF_GREEN = "#34C759"
PERF_RED   = "#FF3B30"
PERF_GRAY  = "#888888"


def get_api_key() -> str:
    try:
        return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        return os.getenv("ANTHROPIC_API_KEY", "")


def load_history() -> list:
    """GitHub 우선 → 로컬 파일 순으로 이력을 불러옵니다."""
    # GitHub 자동 불러오기 (토큰 설정 시)
    if is_configured() and "gh_sha" not in st.session_state:
        gh_history, sha = load_from_github()
        if gh_history:
            st.session_state["gh_sha"] = sha
            save_history_local(gh_history)  # 로컬에도 캐시
            return gh_history
        st.session_state["gh_sha"] = sha  # None 이어도 기록

    # 로컬 파일 fallback
    if HISTORY_PATH.exists():
        try:
            with open(HISTORY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            HISTORY_PATH.unlink(missing_ok=True)
    return []


def save_history_local(history: list) -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def save_history(history: list) -> None:
    """로컬 저장 + GitHub 자동 업로드 (토큰 설정 시)."""
    save_history_local(history)
    if is_configured():
        sha = st.session_state.get("gh_sha")
        new_sha = save_to_github(history, sha)
        if new_sha:
            st.session_state["gh_sha"] = new_sha


def perf_color(val) -> str:
    if val is None:
        return PERF_GRAY
    return PERF_GREEN if val >= 0 else PERF_RED


def fmt_perf(val) -> str:
    if val is None:
        return "—"
    sign = "▲" if val >= 0 else "▼"
    return f"{sign} {abs(val):.2f}%"


def google_news_url(query: str) -> str:
    return f"https://news.google.com/search?q={urllib.parse.quote(query)}&hl=en"


def youtube_url(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ETF 포트폴리오 대시보드 | Turbogenius",
    page_icon="🌐",
    layout="wide",
)

st.markdown("""
<style>
.block-container { padding-top: 1.5rem; }
.card {
    background: #1a1d2e; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 16px; border: 1px solid #2a2d40;
}
.card-sm {
    background: #1a1d2e; border-radius: 10px;
    padding: 14px 18px; border: 1px solid #2a2d40;
}
.metric-tile {
    background: #1a1d2e; border-radius: 10px;
    padding: 14px 18px; text-align: center; border: 1px solid #2a2d40;
}
.metric-label { color: #888; font-size: 0.78rem; margin-bottom: 4px; }
.metric-value { color: #fafafa; font-size: 1.35rem; font-weight: 700; }
.metric-sub   { font-size: 0.82rem; margin-top: 2px; }
.badge {
    display: inline-block; border-radius: 6px;
    padding: 2px 10px; font-size: 0.75rem; font-weight: 600;
}
.badge-green  { background: rgba(52,199,89,0.18);   color: #34C759; }
.badge-orange { background: rgba(255,149,0,0.18);   color: #FF9500; }
.badge-red    { background: rgba(255,59,48,0.18);   color: #FF3B30; }
.badge-blue   { background: rgba(0,122,255,0.18);   color: #0A84FF; }
.badge-gray   { background: rgba(136,136,136,0.18); color: #aaa;   }
.link-row a {
    display: inline-block; background: #252840; color: #a0a8ff !important;
    border-radius: 8px; padding: 6px 14px; margin: 4px 6px 4px 0;
    font-size: 0.82rem; text-decoration: none !important; border: 1px solid #3a3d60;
}
.link-row a:hover { background: #30345a; }
.section-title {
    font-size: 1.05rem; font-weight: 700; color: #fafafa;
    margin-bottom: 10px; display: flex; align-items: center; gap: 8px;
}
.divider { border-top: 1px solid #2a2d40; margin: 20px 0; }
.rebal-row {
    display: flex; align-items: center; gap: 12px;
    padding: 10px 0; border-bottom: 1px solid #22263a;
}
.rebal-ticker { font-weight: 700; font-size: 0.95rem; min-width: 60px; }
.rebal-reason { color: #bbb; font-size: 0.82rem; }

@media print {
    [data-testid="stSidebar"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stButton"],
    [data-testid="stTabs"] .stTabBar,
    .stSpinner,
    footer { display: none !important; }

    body, .stApp { background: #ffffff !important; color: #111 !important; }
    .main .block-container { padding: 0 !important; max-width: 100% !important; }

    .card, .card-sm {
        background: #f8f8f8 !important; color: #111 !important;
        border: 1px solid #ccc !important; break-inside: avoid;
    }
    .metric-tile {
        background: #f8f8f8 !important; border: 1px solid #ccc !important;
        break-inside: avoid;
    }
    .metric-value, .metric-label, .section-title { color: #111 !important; }
    .badge-green  { color: #1a7a30 !important; }
    .badge-orange { color: #a05000 !important; }
    .badge-red    { color: #a01010 !important; }
    .badge-blue   { color: #0055cc !important; }
    .divider { border-color: #ccc !important; }
    .rebal-reason { color: #444 !important; }
    table { color: #111 !important; }
    th, td { border-color: #ccc !important; }
    a { color: #0055cc !important; }
}
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("🌐 ETF 대시보드")
    st.caption("글로벌 트렌드 기반 분기별 포트폴리오")
    st.divider()

    env_key = get_api_key()
    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        value=env_key,
        help="Claude AI 분석에 필요합니다.",
    )

    st.divider()
    st.subheader("포트폴리오 이력")

    history = load_history()
    if history:
        labels = [h.get("quarter_label") or h.get("week_label", f"분석 {i+1}")
                  for i, h in enumerate(history)]
        selected_label = st.selectbox("분기 선택", labels, index=0)
        selected_idx = labels.index(selected_label)
        view_data = history[selected_idx]
    else:
        view_data = None

    st.divider()
    generate_btn = st.button("새 분석 생성", type="primary", use_container_width=True)

    if view_data:
        if st.button("📄 PDF 저장", use_container_width=True,
                     help="브라우저 인쇄 대화상자 → 'PDF로 저장' 선택"):
            st.session_state["_print_pdf"] = True

    if history:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑 이력 전체 삭제", use_container_width=True):
            save_history([])
            st.rerun()

    st.divider()
    if is_configured():
        st.caption("☁️ GitHub 자동 저장 **활성화** — 이력이 영구 보존됩니다.")
    else:
        st.caption("⚠️ GitHub Token 미설정 — 앱 재시작 시 이력이 초기화됩니다.")
        st.caption("💾 Streamlit Cloud Secrets에 `GITHUB_TOKEN`을 추가하면 자동 저장됩니다.")
    if kis_is_configured():
        st.caption("📡 KIS OpenAPI 연결 — 실시간 시세·수급·구성종목·NAV 분석 활성화.")
    else:
        st.caption("ℹ️ KIS API 미설정 — Secrets에 `KIS_APP_KEY` / `KIS_APP_SECRET` 추가 시 심층 분석 활성화.")
    st.caption("📊 시세는 KRX 공식 API 1순위, KIS OpenAPI 보완 (캐시 30분).")


# ── Analysis trigger ──────────────────────────────────────────────────────────

if generate_btn:
    if not api_key:
        st.error("사이드바에 Anthropic API Key를 입력해주세요.")
        st.stop()

    from modules.etf_analyzer import generate_etf_analysis

    prev_portfolio = history[0]["portfolio"] if history else None

    with st.spinner("Claude가 분기 트렌드를 분석 중입니다… (30~60초 소요)"):
        try:
            result = generate_etf_analysis(api_key, prev_portfolio)
            result["generated_at"] = datetime.now().isoformat()
            history.insert(0, result)
            save_history(history)
            view_data = result
            st.success(f"분석 완료: {result.get('quarter_label', '')}")
        except Exception as e:
            st.error(f"분석 생성 실패: {e}")
            st.stop()

# ── No data yet ───────────────────────────────────────────────────────────────

if not view_data:
    st.info(
        "아직 포트폴리오 분석이 없습니다.\n\n"
        "사이드바에 **Anthropic API Key**를 입력한 후 **새 분석 생성** 버튼을 클릭하세요."
    )
    st.stop()


# ═══════════════════════════════════════════════════════════════════════════════
# Main Dashboard
# ═══════════════════════════════════════════════════════════════════════════════

topic = view_data.get("topic", {})
portfolio = view_data.get("portfolio", [])
rebalancing = view_data.get("rebalancing", {})
market_outlook = view_data.get("market_outlook", {})
generated_at = view_data.get("generated_at", "")

# ── Header ────────────────────────────────────────────────────────────────────

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    label = view_data.get("quarter_label") or view_data.get("week_label", "ETF 포트폴리오 대시보드")
    st.markdown(f"## 🌐 {label}")
    if generated_at:
        ts = datetime.fromisoformat(generated_at).strftime("%Y-%m-%d %H:%M")
        st.caption(f"분석 생성: {ts}")
with col_h2:
    risk = market_outlook.get("risk_level", "")
    sentiment = market_outlook.get("sentiment", "")
    risk_cls = {"낮음": "badge-green", "중간": "badge-orange", "높음": "badge-red"}.get(risk, "badge-gray")
    sent_cls = {"강세": "badge-green", "중립": "badge-orange", "약세": "badge-red"}.get(sentiment, "badge-gray")
    st.markdown(
        f'<div style="text-align:right;margin-top:8px">'
        f'<span class="badge {risk_cls}">리스크 {risk}</span>&nbsp;'
        f'<span class="badge {sent_cls}">{sentiment}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Section 1: 이번 분기 테마 ─────────────────────────────────────────────────

st.markdown('<div class="section-title">📰 이번 분기 글로벌 투자 테마</div>', unsafe_allow_html=True)

st.markdown(
    f'<div class="card">'
    f'<div style="font-size:1.25rem;font-weight:700;color:#fafafa;margin-bottom:10px">'
    f'{topic.get("title", "—")}</div>'
    f'<div style="color:#ccc;line-height:1.7;margin-bottom:14px">{topic.get("summary", "")}</div>',
    unsafe_allow_html=True,
)
for pt in topic.get("key_points", []):
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px">'
        f'<span style="color:#FF9500;font-size:1rem;margin-top:2px">▸</span>'
        f'<span style="color:#ddd;font-size:0.9rem">{pt}</span></div>',
        unsafe_allow_html=True,
    )
st.markdown('</div>', unsafe_allow_html=True)

# ── Section 2: 관련 기사 / 유튜브 ────────────────────────────────────────────

col_news, col_yt = st.columns(2)
with col_news:
    st.markdown('<div class="section-title">📄 관련 기사 검색</div>', unsafe_allow_html=True)
    link_items = "".join(
        f'<a href="{google_news_url(q["query"])}" target="_blank" rel="noopener">'
        f'🔍 {q.get("description", q["query"])}</a>'
        for q in topic.get("news_search_queries", [])
    )
    st.markdown(f'<div class="card link-row">{link_items}</div>', unsafe_allow_html=True)

with col_yt:
    st.markdown('<div class="section-title">▶ 유튜브 검색</div>', unsafe_allow_html=True)
    yt_items = "".join(
        f'<a href="{youtube_url(q["query"])}" target="_blank" rel="noopener">'
        f'▶ {q.get("description", q["query"])}</a>'
        for q in topic.get("youtube_search_queries", [])
    )
    st.markdown(f'<div class="card link-row">{yt_items}</div>', unsafe_allow_html=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Section 3: 추천 ETF 포트폴리오 ────────────────────────────────────────────

st.markdown('<div class="section-title">💼 추천 ETF 포트폴리오</div>', unsafe_allow_html=True)

col_pie, col_tbl = st.columns([1, 1.6])
with col_pie:
    if portfolio:
        colors_seq = ["#007AFF", "#FF9500", "#34C759", "#FF3B30",
                      "#AF52DE", "#5AC8FA", "#FF2D55", "#FFD60A"]
        fig_pie = go.Figure(go.Pie(
            labels=[e["ticker"] for e in portfolio],
            values=[e["weight"] for e in portfolio],
            hole=0.45,
            marker=dict(colors=colors_seq[:len(portfolio)],
                        line=dict(color="#0e1117", width=2)),
            textinfo="label+percent",
            textfont=dict(size=13, color="#fafafa"),
            hovertemplate="<b>%{label}</b><br>비중: %{value:.1f}%<extra></extra>",
        ))
        fig_pie.update_layout(
            height=320, margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False, font=dict(color="#fafafa"),
        )
        st.plotly_chart(fig_pie, use_container_width=True)

with col_tbl:
    for e in portfolio:
        risk = e.get("risk_level", "")
        risk_cls = {"낮음": "badge-green", "중간": "badge-orange",
                    "높음": "badge-red"}.get(risk, "badge-gray")
        st.markdown(
            f'<div class="card-sm" style="margin-bottom:8px">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">'
            f'<span style="font-weight:700;font-size:1rem">{e["ticker"]}</span>'
            f'<span style="display:flex;gap:6px;align-items:center">'
            f'<span class="badge badge-blue">{e.get("category","")}</span>'
            f'<span class="badge {risk_cls}">{risk}</span>'
            f'<span style="font-size:1.1rem;font-weight:700;color:#FF9500">{e["weight"]:.1f}%</span>'
            f'</span></div>'
            f'<div style="color:#aaa;font-size:0.78rem;margin-bottom:4px">{e.get("name","")}</div>'
            f'<div style="color:#bbb;font-size:0.82rem;line-height:1.5">{e.get("rationale","")}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Section 4: 리밸런싱 추천 ─────────────────────────────────────────────────

st.markdown('<div class="section-title">🔄 지난 분기 대비 리밸런싱 추천</div>', unsafe_allow_html=True)

action_main = rebalancing.get("action", "—")
action_cls = {"유지": "badge-green", "소폭 조정": "badge-orange",
              "전략 변경": "badge-red"}.get(action_main, "badge-gray")

st.markdown(
    f'<div class="card">'
    f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">'
    f'<span style="font-size:1rem;font-weight:700">전략 판단:</span>'
    f'<span class="badge {action_cls}" style="font-size:0.9rem;padding:4px 14px">{action_main}</span>'
    f'</div>'
    f'<div style="color:#ccc;font-size:0.9rem;line-height:1.7;margin-bottom:14px">'
    f'{rebalancing.get("overall_comment","")}</div>',
    unsafe_allow_html=True,
)

changes = rebalancing.get("changes", [])
if changes:
    for ch in changes:
        delta = ch.get("delta_weight", 0)
        act = ch.get("action", "")
        col = ACTION_COLOR.get(act, "#aaa")
        delta_str = f'+{delta:.1f}%p' if delta > 0 else f'{delta:.1f}%p' if delta < 0 else "—"
        st.markdown(
            f'<div class="rebal-row">'
            f'<span class="rebal-ticker">{ch.get("ticker","")}</span>'
            f'<span class="badge" style="background:rgba(0,0,0,0.3);color:{col};border:1px solid {col}">{act}</span>'
            f'<span style="color:{col};font-weight:600;min-width:60px">{delta_str}</span>'
            f'<span class="rebal-reason">{ch.get("reason","")}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div style="color:#888;font-size:0.9rem">지난 분기 포트폴리오가 없어 비교 데이터가 없습니다. '
        '다음 분기 분석 시 리밸런싱 추천이 표시됩니다.</div>',
        unsafe_allow_html=True,
    )
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Section 5: ETF 시세 & 퍼포먼스 ──────────────────────────────────────────

st.markdown('<div class="section-title">📊 ETF 시세 & 퍼포먼스</div>', unsafe_allow_html=True)

if portfolio:
    tickers_fetch = tuple(e["ticker"] for e in portfolio)
    # AI 이름 기본, KRX 공식 이름으로 덮어쓰기
    etf_names_map = {e["ticker"]: e.get("name", e["ticker"]) for e in portfolio}
    try:
        from modules.krx_data import get_name_map as _krx_name_map
        _krx = _krx_name_map()
        etf_names_map.update({k: v for k, v in _krx.items() if k in etf_names_map})
    except Exception:
        pass

    with st.spinner("시세 데이터 로딩 중…"):
        from modules.etf_fetcher import fetch_etf_performance
        perf_df = fetch_etf_performance(tickers_fetch)

    if perf_df.empty:
        st.warning("시세 데이터를 가져오지 못했습니다. 네트워크를 확인해주세요.")
    else:
        cols_m = st.columns(len(perf_df))
        for col_m, (_, row) in zip(cols_m, perf_df.iterrows()):
            ticker = row["Ticker"]
            price = row.get("Price")
            perf_1w = row.get("1W (%)")
            color = perf_color(perf_1w)
            etf_name = etf_names_map.get(ticker, "")
            # nan/None 모두 처리
            try:
                price_str = f"₩{float(price):,.0f}" if price is not None else "—"
                if price_str == "₩nan":
                    price_str = "—"
            except Exception:
                price_str = "—"
            with col_m:
                st.markdown(
                    f'<div class="metric-tile">'
                    f'<div class="metric-label" style="font-weight:700;color:#fafafa">{ticker}</div>'
                    f'<div class="metric-label" style="font-size:0.72rem;margin-bottom:6px;white-space:nowrap;'
                    f'overflow:hidden;text-overflow:ellipsis">{etf_name}</div>'
                    f'<div class="metric-value">{price_str}</div>'
                    f'<div class="metric-sub" style="color:{color}">{fmt_perf(perf_1w)} (1W)</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size:0.95rem">상세 퍼포먼스</div>',
                    unsafe_allow_html=True)

        display_rows = []
        for _, row in perf_df.iterrows():
            ticker = row["Ticker"]
            weight = next((e["weight"] for e in portfolio if e["ticker"] == ticker), None)
            display_rows.append({
                "티커": ticker,
                "ETF명": etf_names_map.get(ticker, ticker),
                "비중": f"{weight:.1f}%" if weight else "—",
                "현재가 (KRW)": (
                    f"₩{float(row['Price']):,.0f}"
                    if row.get("Price") is not None and str(row['Price']) != "nan"
                    else "—"
                ),
                "1주일": fmt_perf(row.get("1W (%)")),
                "1개월": fmt_perf(row.get("1M (%)")),
                "3개월": fmt_perf(row.get("3M (%)")),
                "1년": fmt_perf(row.get("1Y (%)")),
                "_1w": row.get("1W (%)"), "_1m": row.get("1M (%)"),
                "_3m": row.get("3M (%)"), "_1y": row.get("1Y (%)"),
            })
        disp_df = pd.DataFrame(display_rows)

        header_cols = ["티커", "ETF명", "비중", "현재가 (KRW)", "1주일", "1개월", "3개월", "1년"]
        raw_map = {"1주일": "_1w", "1개월": "_1m", "3개월": "_3m", "1년": "_1y", "현재가 (KRW)": None}
        header_html = "".join(
            f'<th style="text-align:{"left" if c in ("티커","ETF명","비중") else "right"};'
            f'padding:8px 12px;color:#888;font-size:0.78rem;font-weight:600;'
            f'border-bottom:1px solid #2a2d40">{c}</th>'
            for c in header_cols
        )
        rows_html = ""
        for _, r in disp_df.iterrows():
            row_html = ""
            for c in header_cols:
                align = "left" if c in ("티커", "ETF명", "비중") else "right"
                style = f'text-align:{align};padding:8px 12px;font-size:0.88rem;'
                if c in raw_map and raw_map[c] is not None:
                    color = perf_color(r.get(raw_map[c]))
                    style += f"color:{color};font-weight:600;"
                elif c == "티커":
                    style += "font-weight:700;color:#fafafa;"
                elif c == "비중":
                    style += "color:#FF9500;font-weight:600;"
                else:
                    style += "color:#ddd;"
                row_html += f'<td style="{style}">{r[c]}</td>'
            rows_html += f'<tr style="border-bottom:1px solid #1e2130">{row_html}</tr>'

        st.markdown(
            f'<div style="background:#1a1d2e;border-radius:12px;border:1px solid #2a2d40;overflow:hidden">'
            f'<table style="width:100%;border-collapse:collapse">'
            f'<thead><tr>{header_html}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div>',
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title" style="font-size:0.95rem">기간별 수익률 비교</div>',
                    unsafe_allow_html=True)

        periods_map = {"1주일": "1W (%)", "1개월": "1M (%)", "3개월": "3M (%)", "1년": "1Y (%)"}
        for tab, (period_label, col_key) in zip(st.tabs(list(periods_map.keys())), periods_map.items()):
            with tab:
                chart_data = perf_df[["Ticker", col_key]].dropna().sort_values(col_key)
                if chart_data.empty:
                    st.info("데이터 없음")
                    continue
                bar_colors = [PERF_GREEN if v >= 0 else PERF_RED for v in chart_data[col_key]]
                fig_bar = go.Figure(go.Bar(
                    x=chart_data[col_key], y=chart_data["Ticker"], orientation="h",
                    marker_color=bar_colors,
                    text=[f"{v:+.2f}%" for v in chart_data[col_key]],
                    textposition="outside", textfont=dict(color="#fafafa", size=12),
                    hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
                ))
                fig_bar.update_layout(
                    height=max(220, len(chart_data) * 50),
                    margin=dict(l=10, r=60, t=10, b=10),
                    xaxis=dict(gridcolor="#1e2130", zeroline=True,
                               zerolinecolor="#444", ticksuffix="%"),
                    yaxis=dict(showgrid=False),
                    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#fafafa"),
                )
                st.plotly_chart(fig_bar, use_container_width=True)

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Section 5.5: KIS 기반 개별 ETF 심층 분석 ─────────────────────────────────

if portfolio and kis_is_configured():
    st.markdown(
        '<div class="section-title">🔬 개별 ETF 심층 분석 '
        '<span style="font-size:0.7rem;color:#888;font-weight:400">(KIS OpenAPI)</span></div>',
        unsafe_allow_html=True,
    )

    sel_options = [f"{e['ticker']} | {e.get('name', '')}" for e in portfolio]
    sel_choice  = st.selectbox("분석할 ETF 선택", sel_options, key="kis_etf_select")
    sel_ticker  = sel_choice.split(" | ")[0]

    tab_flow, tab_comp, tab_nav = st.tabs([
        "📈 외국인·기관 수급",
        "📋 구성종목 (PDF)",
        "💎 NAV 추이 / 괴리율",
    ])

    # ── 외국인·기관 순매수 ───────────────────────────────────────────────────
    with tab_flow:
        with st.spinner("수급 데이터 조회 중…"):
            flow_df = get_investor_flow(sel_ticker)

        if flow_df.empty:
            st.info("수급 데이터를 가져오지 못했습니다. (KIS 모의투자 미지원 또는 비정상 종목)")
        else:
            recent = flow_df.tail(20).copy()
            sum_fgn = int(recent["foreign_net"].sum())
            sum_org = int(recent["institutional_net"].sum())
            sum_ind = int(recent["individual_net"].sum())

            c1, c2, c3 = st.columns(3)
            for col, label, val, neg_color in (
                (c1, "외국인 (20일 누적)",  sum_fgn, "#FF3B30"),
                (c2, "기관 (20일 누적)",    sum_org, "#FF3B30"),
                (c3, "개인 (20일 누적)",    sum_ind, "#FF3B30"),
            ):
                color = "#34C759" if val >= 0 else neg_color
                sign  = "▲" if val >= 0 else "▼"
                with col:
                    st.markdown(
                        f'<div class="metric-tile">'
                        f'<div class="metric-label">{label}</div>'
                        f'<div class="metric-value" style="color:{color}">{sign} {abs(val):,}주</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            fig_flow = go.Figure()
            for col, name, color in (
                ("foreign_net",       "외국인", "#FF9500"),
                ("institutional_net", "기관",   "#007AFF"),
                ("individual_net",    "개인",   "#888888"),
            ):
                fig_flow.add_trace(go.Bar(
                    x=recent["date"], y=recent[col],
                    name=name, marker_color=color,
                    hovertemplate=f"{name}: %{{y:,}}주<extra></extra>",
                ))
            fig_flow.update_layout(
                height=320, barmode="group",
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#fafafa"),
                xaxis=dict(gridcolor="#1e2130"),
                yaxis=dict(title="순매수 (주)", gridcolor="#1e2130", zeroline=True, zerolinecolor="#444"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_flow, use_container_width=True)

    # ── ETF 구성종목 ─────────────────────────────────────────────────────────
    with tab_comp:
        with st.spinner("구성종목 PDF 조회 중…"):
            comp_df = get_etf_components(sel_ticker)

        if comp_df.empty:
            st.info("구성종목 데이터를 가져오지 못했습니다.")
        else:
            top10 = comp_df.head(10)
            total_weight = comp_df["weight"].sum()

            st.markdown(
                f'<div class="card-sm" style="margin-bottom:14px">'
                f'<span style="color:#888">총 구성종목: </span>'
                f'<span style="color:#fafafa;font-weight:700">{len(comp_df)}개</span>&nbsp;&nbsp;'
                f'<span style="color:#888">상위 10종목 비중: </span>'
                f'<span style="color:#FF9500;font-weight:700">{top10["weight"].sum():.1f}%</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            header_html = "".join(
                f'<th style="text-align:{"left" if c in ("코드","종목명") else "right"};'
                f'padding:8px 12px;color:#888;font-size:0.78rem;font-weight:600;'
                f'border-bottom:1px solid #2a2d40">{c}</th>'
                for c in ("코드", "종목명", "비중 (%)", "보유주수", "현재가")
            )
            rows_html = ""
            for _, r in top10.iterrows():
                rows_html += (
                    f'<tr style="border-bottom:1px solid #1e2130">'
                    f'<td style="padding:8px 12px;color:#fafafa;font-weight:600;font-size:0.88rem">{r["code"]}</td>'
                    f'<td style="padding:8px 12px;color:#ddd;font-size:0.88rem">{r["name"]}</td>'
                    f'<td style="padding:8px 12px;text-align:right;color:#FF9500;font-weight:600;font-size:0.88rem">'
                    f'{r["weight"]:.2f}</td>'
                    f'<td style="padding:8px 12px;text-align:right;color:#ddd;font-size:0.88rem">{r["shares"]:,.0f}</td>'
                    f'<td style="padding:8px 12px;text-align:right;color:#ddd;font-size:0.88rem">'
                    f'₩{r["price"]:,.0f}</td></tr>'
                )
            st.markdown(
                f'<div style="background:#1a1d2e;border-radius:12px;border:1px solid #2a2d40;overflow:hidden">'
                f'<table style="width:100%;border-collapse:collapse">'
                f'<thead><tr>{header_html}</tr></thead>'
                f'<tbody>{rows_html}</tbody></table></div>',
                unsafe_allow_html=True,
            )

            # 상위 10 도넛 차트
            st.markdown("<br>", unsafe_allow_html=True)
            fig_comp = go.Figure(go.Pie(
                labels=top10["name"], values=top10["weight"],
                hole=0.5,
                marker=dict(line=dict(color="#0e1117", width=2)),
                textinfo="label+percent",
                hovertemplate="<b>%{label}</b><br>비중: %{value:.2f}%<extra></extra>",
            ))
            fig_comp.update_layout(
                height=380, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False, font=dict(color="#fafafa", size=11),
            )
            st.plotly_chart(fig_comp, use_container_width=True)

    # ── NAV 추이 / 괴리율 ────────────────────────────────────────────────────
    with tab_nav:
        with st.spinner("NAV 데이터 조회 중…"):
            nav_df = get_etf_nav_trend(sel_ticker)
            cur_info = get_current_price(sel_ticker)

        if nav_df.empty:
            # Fallback: 단일 시점 NAV vs 현재가
            if cur_info and cur_info.get("nav") and cur_info.get("price"):
                price  = cur_info["price"]
                nav    = cur_info["nav"]
                premium = (price / nav - 1) * 100
                color  = "#FF3B30" if premium > 0.5 else ("#007AFF" if premium < -0.5 else "#34C759")
                st.markdown(
                    f'<div class="card">'
                    f'<div style="display:flex;justify-content:space-around;text-align:center">'
                    f'<div><div class="metric-label">현재가</div>'
                    f'<div class="metric-value">₩{price:,.0f}</div></div>'
                    f'<div><div class="metric-label">NAV</div>'
                    f'<div class="metric-value">₩{nav:,.0f}</div></div>'
                    f'<div><div class="metric-label">괴리율</div>'
                    f'<div class="metric-value" style="color:{color}">{premium:+.3f}%</div></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                st.caption("⚠️ NAV 일별 추이 API가 응답하지 않아 단일 시점만 표시합니다.")
            else:
                st.info("NAV 데이터를 가져오지 못했습니다.")
        else:
            latest = nav_df.iloc[-1]
            avg_premium = nav_df["premium"].mean()
            max_premium = nav_df["premium"].max()
            min_premium = nav_df["premium"].min()

            c1, c2, c3, c4 = st.columns(4)
            cur_prem = latest["premium"]
            cur_color = "#FF3B30" if cur_prem > 0.5 else ("#007AFF" if cur_prem < -0.5 else "#34C759")
            for col, label, val, color in (
                (c1, "현재 괴리율",  f"{cur_prem:+.3f}%", cur_color),
                (c2, "평균 괴리율",  f"{avg_premium:+.3f}%", "#aaa"),
                (c3, "최대 프리미엄", f"{max_premium:+.3f}%", "#FF3B30"),
                (c4, "최대 디스카운트", f"{min_premium:+.3f}%", "#007AFF"),
            ):
                with col:
                    st.markdown(
                        f'<div class="metric-tile">'
                        f'<div class="metric-label">{label}</div>'
                        f'<div class="metric-value" style="color:{color};font-size:1.2rem">{val}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("<br>", unsafe_allow_html=True)

            fig_nav = go.Figure()
            fig_nav.add_trace(go.Scatter(
                x=nav_df["date"], y=nav_df["close"],
                name="시장가", line=dict(color="#FF9500", width=2),
                hovertemplate="시장가: ₩%{y:,.0f}<extra></extra>",
            ))
            fig_nav.add_trace(go.Scatter(
                x=nav_df["date"], y=nav_df["nav"],
                name="NAV", line=dict(color="#007AFF", width=2, dash="dot"),
                hovertemplate="NAV: ₩%{y:,.0f}<extra></extra>",
            ))
            fig_nav.update_layout(
                height=300, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#fafafa"),
                xaxis=dict(gridcolor="#1e2130"),
                yaxis=dict(title="가격 (KRW)", gridcolor="#1e2130"),
                legend=dict(orientation="h", y=1.1),
            )
            st.plotly_chart(fig_nav, use_container_width=True)

            # 괴리율 추이
            fig_prem = go.Figure(go.Bar(
                x=nav_df["date"], y=nav_df["premium"],
                marker_color=[PERF_RED if v > 0 else "#007AFF" for v in nav_df["premium"]],
                hovertemplate="괴리율: %{y:+.3f}%<extra></extra>",
            ))
            fig_prem.update_layout(
                height=220, margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#fafafa"),
                xaxis=dict(gridcolor="#1e2130"),
                yaxis=dict(title="괴리율 (%)", gridcolor="#1e2130",
                          zeroline=True, zerolinecolor="#444", ticksuffix="%"),
            )
            st.plotly_chart(fig_prem, use_container_width=True)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

# ── Section 6: 시장 전망 ─────────────────────────────────────────────────────

st.markdown('<div class="section-title">🔭 시장 전망 & 리스크/기회 요인</div>', unsafe_allow_html=True)

col_risk_list, col_opp_list = st.columns(2)
with col_risk_list:
    st.markdown('<div class="card"><div style="font-weight:700;margin-bottom:10px;color:#FF3B30">⚠ 주요 리스크</div>',
                unsafe_allow_html=True)
    for item in market_outlook.get("key_risks", []):
        st.markdown(
            f'<div style="display:flex;gap:8px;margin-bottom:6px">'
            f'<span style="color:#FF3B30">•</span>'
            f'<span style="color:#ddd;font-size:0.88rem">{item}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

with col_opp_list:
    st.markdown('<div class="card"><div style="font-weight:700;margin-bottom:10px;color:#34C759">✦ 투자 기회</div>',
                unsafe_allow_html=True)
    for item in market_outlook.get("opportunities", []):
        st.markdown(
            f'<div style="display:flex;gap:8px;margin-bottom:6px">'
            f'<span style="color:#34C759">•</span>'
            f'<span style="color:#ddd;font-size:0.88rem">{item}</span></div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────

st.markdown(
    '<div style="text-align:center;color:#555;font-size:0.78rem;margin-top:24px">'
    '본 대시보드는 AI 분석 결과로, 투자 권고가 아닙니다. '
    '모든 투자 결정은 본인 책임 하에 이루어져야 합니다.'
    '</div>',
    unsafe_allow_html=True,
)

# ── PDF 인쇄 트리거 (모든 콘텐츠 렌더링 후 실행) ────────────────────────────────
if st.session_state.pop("_print_pdf", False):
    import streamlit.components.v1 as _components
    _components.html(
        "<script>window.parent.print();</script>",
        height=0,
    )
