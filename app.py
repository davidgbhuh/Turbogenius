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

    # 이력 불러오기
    uploaded = st.file_uploader(
        "📤 이력 불러오기 (.json)",
        type="json",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        try:
            imported = json.load(uploaded)
            if isinstance(imported, list) and imported:
                save_history(imported)
                st.success("이력을 불러왔습니다!")
                st.rerun()
        except Exception:
            st.error("파일 형식이 올바르지 않습니다.")

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

    # 이력 저장 / 이메일 보내기
    if history:
        history_json = json.dumps(history, ensure_ascii=False, indent=2)
        filename = f"etf_history_{datetime.now().strftime('%Y%m%d')}.json"

        st.download_button(
            label="📥 이력 저장 (파일)",
            data=history_json,
            file_name=filename,
            mime="application/json",
            use_container_width=True,
        )

        st.markdown("**📨 이력 이메일로 보내기**")
        email_to = st.text_input(
            "받는 이메일 주소",
            placeholder="example@email.com",
            label_visibility="collapsed",
        )
        if email_to:
            latest = history[0]
            qlabel = latest.get("quarter_label", "")
            topic_title = latest.get("topic", {}).get("title", "")
            pf_lines = "\n".join(
                f"  {e['ticker']} {e.get('name','')} {e['weight']}%"
                for e in latest.get("portfolio", [])
            )
            body = (
                f"[ETF 포트폴리오 이력]\n\n"
                f"분기: {qlabel}\n테마: {topic_title}\n\n"
                f"포트폴리오:\n{pf_lines}\n\n"
                f"전체 이력 JSON은 파일 저장 후 첨부하세요."
            )
            subject = urllib.parse.quote(f"ETF 포트폴리오 이력 - {qlabel}")
            body_enc = urllib.parse.quote(body)
            mailto_url = f"mailto:{email_to}?subject={subject}&body={body_enc}"
            st.markdown(
                f'<a href="{mailto_url}" target="_blank" '
                f'style="display:block;text-align:center;background:#FF9500;'
                f'color:#fff;border-radius:8px;padding:10px;'
                f'font-weight:700;text-decoration:none;margin-top:6px">'
                f'📨 이메일 앱으로 보내기</a>',
                unsafe_allow_html=True,
            )

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
    st.caption("ℹ️ 현재가는 KRX 공식 API 기준 (최대 1시간 캐시), 수익률은 yfinance 기준입니다.")


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
