"""Korean stock search via Naver Finance API, with hardcoded fallback."""

import streamlit as st
import pandas as pd
import requests

_NAVER_SEARCH_URL = "https://ac.stock.naver.com/ac"
_NAVER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def search_naver(query: str) -> pd.DataFrame:
    """Search stocks using Naver Finance autocomplete API.

    Returns DataFrame with [ticker, name] or empty DataFrame on failure.
    """
    try:
        resp = requests.get(
            _NAVER_SEARCH_URL,
            headers=_NAVER_HEADERS,
            params={"q": query, "target": "stock"},
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])
        # items는 [[code, name, ...], ...] 형태
        records = []
        for item in items:
            if len(item) >= 2:
                code = item[0]
                name = item[1]
                if len(code) == 6 and code.isdigit():
                    records.append({"ticker": code, "name": name})
        return pd.DataFrame(records)
    except Exception:
        return pd.DataFrame()


# ── Hardcoded fallback ─────────────────────────────────────────────────────
_FALLBACK = {
    "KOSPI": [
        ("005930", "삼성전자"), ("000660", "SK하이닉스"), ("005380", "현대차"),
        ("005490", "POSCO홀딩스"), ("051910", "LG화학"), ("035420", "NAVER"),
        ("000270", "기아"), ("068270", "셀트리온"), ("105560", "KB금융"),
        ("055550", "신한지주"), ("012330", "현대모비스"), ("028260", "삼성물산"),
        ("066570", "LG전자"), ("032830", "삼성생명"), ("017670", "SK텔레콤"),
        ("030200", "KT"), ("003550", "LG"), ("096770", "SK이노베이션"),
        ("009150", "삼성전기"), ("018260", "삼성에스디에스"),
        ("373220", "LG에너지솔루션"), ("207940", "삼성바이오로직스"),
        ("000810", "삼성화재"), ("034730", "SK"), ("011200", "HMM"),
        ("086790", "하나금융지주"), ("316140", "우리금융지주"), ("024110", "기업은행"),
        ("139480", "이마트"), ("004020", "현대제철"), ("006400", "삼성SDI"),
        ("010950", "S-Oil"), ("003490", "대한항공"), ("010130", "고려아연"),
        ("000100", "유한양행"), ("002790", "아모레퍼시픽"), ("004170", "신세계"),
        ("009540", "HD한국조선해양"), ("042660", "한화오션"), ("003670", "포스코퓨처엠"),
        ("000120", "CJ대한통운"), ("097950", "CJ제일제당"), ("021240", "코웨이"),
        ("033780", "KT&G"), ("271560", "오리온"), ("007310", "오뚜기"),
        ("004990", "롯데지주"), ("023530", "롯데쇼핑"), ("001450", "현대해상"),
        ("005940", "NH투자증권"), ("016360", "삼성증권"), ("071050", "한국금융지주"),
        ("006360", "GS건설"), ("000720", "현대건설"), ("028050", "삼성엔지니어링"),
        ("047040", "대우건설"), ("009830", "한화솔루션"), ("329180", "현대중공업"),
        ("267250", "HD현대"), ("047050", "포스코인터내셔널"), ("011170", "롯데케미칼"),
        ("180640", "한진칼"), ("002380", "KCC"), ("000080", "하이트진로"),
        ("008770", "호텔신라"), ("024720", "코오롱"), ("001040", "CJ"),
        ("010060", "OCI홀딩스"), ("000990", "DB하이텍"), ("161390", "한국타이어앤테크놀로지"),
    ],
    "KOSDAQ": [
        ("035720", "카카오"), ("247540", "에코프로비엠"), ("086520", "에코프로"),
        ("196170", "알테오젠"), ("091990", "셀트리온헬스케어"), ("028300", "HLB"),
        ("263750", "펄어비스"), ("041510", "에스엠"), ("035900", "JYP Ent"),
        ("122870", "와이지엔터테인먼트"), ("112040", "위메이드"), ("095660", "네오위즈"),
        ("293490", "카카오게임즈"), ("214150", "클래시스"), ("145020", "휴젤"),
        ("357780", "솔브레인"), ("192820", "코스맥스"), ("141080", "레고켐바이오"),
        ("058470", "리노공업"), ("131970", "테크윙"), ("039030", "이오테크닉스"),
        ("053800", "안랩"), ("078340", "컴투스"), ("036570", "엔씨소프트"),
        ("251270", "넷마블"), ("259960", "크래프톤"), ("352820", "하이브"),
        ("035760", "CJ ENM"), ("067160", "아프리카TV"), ("039200", "오스코텍"),
        ("084370", "유진테크"), ("064550", "바이오니아"), ("009420", "한올바이오파마"),
        ("214370", "케어젠"), ("048410", "현대바이오"), ("145720", "덴티움"),
        ("140910", "에스티팜"), ("200130", "콜마비앤에이치"), ("060260", "에이텀"),
        ("950160", "코오롱티슈진"), ("226950", "올릭스"), ("145170", "피엔티"),
        ("119610", "인터로조"), ("038870", "에코마케팅"), ("078160", "메디톡스"),
        ("091700", "파미셀"), ("226340", "본느"), ("054620", "APS홀딩스"),
        ("084010", "대한제강"), ("067630", "HLB생명과학"), ("217270", "넵튠"),
        ("240810", "원익IPS"), ("319400", "현대무벡스"), ("054040", "한국전자금융"),
        ("064260", "다날"), ("950130", "엑세스바이오"), ("215600", "신라젠"),
        ("108675", "LG디스플레이우"), ("060310", "3S"), ("078130", "대웅"),
        ("016670", "디에이테크놀로지"), ("032640", "LG유플러스"), ("010280", "아이티센"),
        ("053210", "스카이라이프"), ("236810", "엔비티"), ("950200", "파나진"),
    ],
}


@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_list(market: str) -> pd.DataFrame:
    """Return full stock list for the given market (hardcoded fallback)."""
    records = [{"ticker": t, "name": n} for t, n in _FALLBACK.get(market, [])]
    return pd.DataFrame(records)


def search_stocks(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Search stock list locally, then supplement with Naver Finance API."""
    if not query or not query.strip():
        return df

    q = query.strip()

    # 1) 로컬 필터
    mask = (
        df["ticker"].str.contains(q, case=False)
        | df["name"].str.contains(q, case=False)
    )
    local_results = df[mask].reset_index(drop=True)

    # 2) Naver Finance API로 추가 검색 (인터넷 연결 시)
    naver_results = search_naver(q)

    if naver_results.empty:
        return local_results

    # 3) 두 결과 합치기 (중복 제거)
    combined = pd.concat([local_results, naver_results], ignore_index=True)
    combined = combined.drop_duplicates(subset="ticker").reset_index(drop=True)
    return combined
