import os
import re
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
API_KEY_DIR = BASE_DIR.parent / "00 API Key"
DATA_DIR = BASE_DIR / "data"

def get_api_key(service_name: str) -> str:
    """
    서비스별 API 키를 Streamlit Secrets, 환경변수, 로컬 파일, Fallback 키에서 견고하게 로드합니다.
    """
    s_upper = service_name.upper()
    
    # 1. Streamlit Secrets (Streamlit Cloud 환경)
    try:
        import streamlit as st
        # 다양한 키 네이밍 허용 (대소문자, 언더스코어 유무 등)
        candidates = [
            f"{s_upper}_API_KEY",
            f"{service_name.lower()}_api_key",
            f"{s_upper}_KEY",
            f"{service_name.lower()}_key",
            s_upper,
            service_name.lower()
        ]
        if hasattr(st, "secrets"):
            for cand in candidates:
                try:
                    if cand in st.secrets:
                        val = str(st.secrets[cand]).strip().strip('"').strip("'")
                        if val:
                            return val
                except Exception:
                    pass
    except Exception:
        pass

    # 2. OS 환경 변수
    env_key = os.getenv(f"{s_upper}_API_KEY")
    if env_key:
        return env_key.strip()
    
    # 3. 로컬 00 API Key 디렉토리 탐색 (로컬 PC 환경)
    if API_KEY_DIR.exists():
        if s_upper == "FRED":
            fred_file = API_KEY_DIR / "FRED StLouis ID&PW.txt"
            if fred_file.exists():
                try:
                    text = fred_file.read_text(encoding="utf-8")
                    match = re.search(r"API\s*Key\s*:\s*([a-zA-Z0-9]+)", text, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
                except Exception:
                    pass
        elif s_upper in ["BOK", "ECOS"]:
            bok_file = API_KEY_DIR / "BOK ID&PW.txt"
            if bok_file.exists():
                try:
                    text = bok_file.read_text(encoding="utf-8")
                    match = re.search(r"API\s*key\s*:\s*([a-zA-Z0-9]+)", text, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
                except Exception:
                    pass
                    
    # 4. 안전 Fallback 기본 키 (Streamlit Cloud Secrets 미등록/오타 시에도 무조건 정상 작동 보장)
    fallback_keys = {
        "FRED": "e3943bacc057203533b1862c61d765f0",
        "BOK": "X8UI0HG69YU5IW03XDNV"
    }
    return fallback_keys.get(s_upper, "")

def get_fred_api_key() -> str:
    return get_api_key("FRED")

def get_bok_api_key() -> str:
    return get_api_key("BOK")

def setup_krx_credentials():
    """
    KRX 계정 정보(ID, PW)를 Streamlit Secrets, 환경변수, 로컬 파일, Fallback에서 로드하여 os.environ에 등록합니다.
    """
    krx_id, krx_pw = "", ""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            krx_id = str(st.secrets.get("KRX_ID", "") or st.secrets.get("krx_id", "")).strip()
            krx_pw = str(st.secrets.get("KRX_PW", "") or st.secrets.get("krx_pw", "")).strip()
    except Exception:
        pass
        
    if not krx_id:
        krx_id = os.getenv("KRX_ID", "").strip()
    if not krx_pw:
        krx_pw = os.getenv("KRX_PW", "").strip()
        
    if (not krx_id or not krx_pw) and API_KEY_DIR.exists():
        krx_file = API_KEY_DIR / "KRX ID&PW.txt"
        if krx_file.exists():
            try:
                text = krx_file.read_text(encoding="utf-8")
                id_m = re.search(r"ID\s*:\s*([^\r\n]+)", text)
                pw_m = re.search(r"PW\s*:\s*([^\r\n]+)", text)
                if id_m:
                    krx_id = id_m.group(1).strip()
                if pw_m:
                    krx_pw = pw_m.group(1).strip()
            except Exception:
                pass
                
    if not krx_id:
        krx_id = "sonoskrx"
    if not krx_pw:
        krx_pw = "99soKRX#1"
        
    os.environ["KRX_ID"] = krx_id
    os.environ["KRX_PW"] = krx_pw
    return krx_id, krx_pw

FRED_API_KEY = get_fred_api_key()
BOK_API_KEY = get_bok_api_key()
setup_krx_credentials()

# 1990년 1월 1일 기본 시작일 (1990년대 초 리세션 및 90년대 후반 외환위기 분석 지원)
DEFAULT_START_DATE = "1990-01-01"

# 지표 레지스트리 (추후 20개 이상 쉽게 확장 가능하도록 설계)
INDICATORS = {
    "FED Target Rate & T10Y Yield & S&P 500": {
        "category": "금리 & 주가",
        "description": "미국 연준 기준금리(FED Target Rate), 미국 10년물 국채 수익률(T10Y Yield), 그리고 S&P 500 주가지수의 추이를 함께 비교합니다. 금리 인상/인하 사이클과 주식 시장의 장기 상관관계를 분석하는 핵심 지표입니다.",
        "chart_type": "dual_axis",
        "series": [
            {
                "id": "FED_TARGET",
                "name": "FED Target Rate",
                "source": "FRED",
                "axis": "y1",
                "color": "#38bdf8", # Sky Blue
                "unit": "%",
                "line_shape": "hv", # 계단형
                "width": 2.2
            },
            {
                "id": "DGS10",
                "name": "T10Y Yield (10년물 국채)",
                "source": "FRED",
                "axis": "y1",
                "color": "#fbbf24", # Amber
                "unit": "%",
                "line_shape": "linear",
                "width": 1.8
            },
            {
                "id": "SP500",
                "name": "S&P 500",
                "source": "YAHOO",
                "ticker": "^GSPC",
                "axis": "y2",
                "color": "#4ade80", # Emerald Green
                "unit": "pt",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "금리 / 수익률 (%)",
        "y2_label": "S&P 500 지수 (pt)",
        "supports_log_scale": True
    },
    "FED Target Rate & BOK Target Rate": {
        "category": "기준금리",
        "description": "미국 연방준비제도(FED)의 기준금리와 한국은행(BOK)의 기준금리를 직접 비교합니다. 한미 금리 역전 현상 및 자본 유출입, 환율 압력의 배경이 되는 금리차(Spread)를 직관적으로 확인할 수 있습니다.",
        "chart_type": "single_axis",
        "series": [
            {
                "id": "FED_TARGET",
                "name": "미국 연준 기준금리 (FED Target)",
                "source": "FRED",
                "axis": "y1",
                "color": "#38bdf8", # Sky Blue
                "unit": "%",
                "line_shape": "hv",
                "width": 2.2
            },
            {
                "id": "BOK_RATE",
                "name": "한국은행 기준금리 (BOK Rate)",
                "source": "BOK",
                "axis": "y1",
                "color": "#f87171", # Rose/Red
                "unit": "%",
                "line_shape": "hv",
                "width": 2.2
            }
        ],
        "y1_label": "기준금리 (%)",
        "show_spread_option": True,
        "spread_name": "한미 금리차 (FED - BOK)"
    },
    "US Treasury Yield Curve (10Y, 2Y, 3M)": {
        "category": "금리 & 수익률곡선",
        "description": "미국 국채 장기(10년물), 중기(2년물), 단기(3개월물) 수익률 곡선을 한 화면에서 비교합니다. 단기 금리가 장기 금리를 웃도는 장단기 금리 역전 현상과 통화정책 기조를 선제적으로 모니터링합니다.",
        "chart_type": "single_axis",
        "series": [
            {
                "id": "DGS10",
                "name": "10-Year Treasury Yield (DGS10)",
                "source": "FRED",
                "axis": "y1",
                "color": "#38bdf8", # Sky Blue
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "DGS2",
                "name": "2-Year Treasury Yield (DGS2)",
                "source": "FRED",
                "axis": "y1",
                "color": "#fbbf24", # Amber
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "DGS3MO",
                "name": "3-Month Treasury Yield (DGS3MO)",
                "source": "FRED",
                "axis": "y1",
                "color": "#f43f5e", # Rose
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "미국 국채 수익률 (%)"
    },
    "T10Y-T2Y Yield Spread & S&P 500": {
        "category": "경기 선행지표",
        "description": "미국 10년물 국채와 2년물 국채의 금리 스프레드(T10Y-T2Y)와 S&P 500 지수를 대조합니다. 장단기 금리 역전(0% 이하 하회)은 역사적으로 가장 신뢰받는 경기 침체의 선행 신호입니다.",
        "chart_type": "dual_axis",
        "series": [
            {
                "id": "T10Y2Y",
                "name": "T10Y-T2Y Yield Spread",
                "source": "FRED",
                "axis": "y1",
                "color": "#818cf8", # Indigo
                "unit": "%p",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "SP500",
                "name": "S&P 500",
                "source": "YAHOO",
                "ticker": "^GSPC",
                "axis": "y2",
                "color": "#4ade80", # Emerald Green
                "unit": "pt",
                "line_shape": "linear",
                "width": 1.8
            }
        ],
        "y1_label": "장단기 금리차 (%p)",
        "y2_label": "S&P 500 지수 (pt)",
        "highlight_zero_line": True,
        "highlight_inversion": True,
        "supports_log_scale": True
    },
    "US Dollar Index & USD/KRW Exchange Rate": {
        "category": "통화 & 외환",
        "description": "글로벌 주요 통화 대비 달러 가치를 나타내는 미국 달러 인덱스(DXY)와 원/달러 환율(USD/KRW)의 통합 비교 차트입니다. 글로벌 달러 강세 주기와 원화 가치의 역사적 동조화 및 변동성을 한눈에 분석할 수 있습니다.",
        "chart_type": "dual_axis",
        "series": [
            {
                "id": "DXY",
                "name": "US Dollar Index (DXY)",
                "source": "YAHOO",
                "ticker": "DX-Y.NYB",
                "axis": "y1",
                "color": "#facc15", # Yellow
                "unit": "pt",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "USDKRW",
                "name": "USD/KRW 환율",
                "source": "FRED",
                "fred_id": "DEXKOUS",
                "axis": "y2",
                "color": "#2dd4bf", # Teal
                "unit": "원",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "달러 인덱스 (pt)",
        "y2_label": "원/달러 환율 (KRW)",
        "show_moving_averages": True
    },
    "Crude Oil Prices: (WTI)": {
        "category": "원자재 & 에너지",
        "description": "서부 텍사스산 원유(WTI) 가격 추이입니다. 미국 에너지정보청(EIA)의 FRED 장기 현물 데이터(1990년~)와 Yahoo Finance의 최신 원유 선물(CL=F)을 스마트 결합하여 걸프전 유가 쇼크부터 최신 거래일 가격까지 단절 없이 실시간으로 분석합니다.",
        "chart_type": "single_axis",
        "series": [
            {
                "id": "WTI",
                "name": "WTI 유가 (Crude Oil)",
                "source": "FRED+YAHOO",
                "axis": "y1",
                "color": "#fb923c", # Orange
                "unit": "$",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "WTI 유가 ($/배럴)",
        "show_moving_averages": True
    },
    "GOLD (GC=F) & Bitcoin (BTC-USD)": {
        "category": "대체자산 & 유동성",
        "description": "전통적 실물 안전자산이자 인플레이션 헤지 수단인 금(Gold 선물, GC=F)과 디지털 자산의 대표격인 비트코인(BTC-USD)의 가격 추이를 비교합니다. 글로벌 통화 완화와 유동성 공급 주기의 척도로 활용됩니다.",
        "chart_type": "dual_axis",
        "series": [
            {
                "id": "GOLD",
                "name": "금 선물 (Gold, GC=F)",
                "source": "YAHOO",
                "ticker": "GC=F",
                "axis": "y1",
                "color": "#fbbf24", # Gold
                "unit": "$/oz",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "BITCOIN",
                "name": "비트코인 (Bitcoin, BTC-USD)",
                "source": "YAHOO",
                "ticker": "BTC-USD",
                "axis": "y2",
                "color": "#f97316", # Orange
                "unit": "$",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "Gold ($/oz)",
        "y2_label": "Bitcoin ($)",
        "supports_log_scale": True
    },
    "Philadelphia Semiconductor Index (SOX) & NASDAQ": {
        "category": "글로벌 테크 & 경기 선행",
        "description": "글로벌 반도체 대표 30개 기업으로 구성된 필라델피아 반도체 지수(SOX)와 기술주 중심의 나스닥 종합지수(NASDAQ)를 통합 비교합니다. 반도체 사이클이 나스닥 지수 및 글로벌 기술주 시장을 어떻게 선행하여 견인하는지 한눈에 분석할 수 있습니다.",
        "chart_type": "dual_axis",
        "series": [
            {
                "id": "SOX",
                "name": "필라델피아 반도체 지수 (SOX)",
                "source": "YAHOO",
                "ticker": "^SOX",
                "axis": "y1",
                "color": "#a855f7", # Purple
                "unit": "pt",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "NASDAQ",
                "name": "나스닥 종합지수 (NASDAQ)",
                "source": "YAHOO",
                "ticker": "^IXIC",
                "axis": "y2",
                "color": "#38bdf8", # Sky Blue
                "unit": "pt",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "SOX 지수 (pt)",
        "y2_label": "NASDAQ 종합지수 (pt)",
        "supports_log_scale": True,
        "log_scale_axis": "both",
        "log_scale_target": "SOX & NASDAQ",
        "show_moving_averages": True
    },
    "Producer Price Index (PPI)": {
        "category": "물가 & 인플레이션",
        "description": "미국 생산자물가지수(PPI) 전체(Total)와 식품 및 에너지를 제외한 근원(Core) 생산자물가의 전년 동월 대비 상승률(YoY %)입니다. 소비자물가(CPI)에 선행하는 기업 제조원가 압력을 측정합니다.",
        "chart_type": "single_axis",
        "show_target_line": True,
        "series": [
            {
                "id": "PPI_TOTAL",
                "name": "PPI Total (최종수요, 전년비)",
                "source": "FRED",
                "fred_id": "PPIFIS",
                "units": "pc1",
                "axis": "y1",
                "color": "#38bdf8", # Sky Blue
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "PPI_CORE",
                "name": "Core PPI (근원, 전년비)",
                "source": "FRED",
                "fred_id": "PPIFES",
                "units": "pc1",
                "axis": "y1",
                "color": "#f43f5e", # Rose/Red
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "생산자물가 상승률 YoY (%)"
    },
    "Consumer Price Index (CPI)": {
        "category": "물가 & 인플레이션",
        "description": "미국 소비자물가지수(CPI) 헤드라인 전체(Total)와 변동성이 큰 식품·에너지를 제외한 근원(Core) CPI의 전년 동월 대비 상승률(YoY %)입니다. 시장 금리와 연준 통화정책에 직접적인 영향을 미칩니다.",
        "chart_type": "single_axis",
        "show_target_line": True,
        "series": [
            {
                "id": "CPI_TOTAL",
                "name": "CPI Total (헤드라인, 전년비)",
                "source": "FRED",
                "fred_id": "CPIAUCNS",
                "units": "pc1",
                "axis": "y1",
                "color": "#38bdf8", # Sky Blue
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "CPI_CORE",
                "name": "Core CPI (근원, 전년비)",
                "source": "FRED",
                "fred_id": "CPILFENS",
                "units": "pc1",
                "axis": "y1",
                "color": "#f43f5e", # Rose/Red
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "소비자물가 상승률 YoY (%)"
    },
    "Personal Consumption Expenditures (PCE)": {
        "category": "물가 & 인플레이션",
        "description": "미국 개인소비지출(PCE) 물가지수 전체(Total)와 근원(Core) PCE의 전년 동월 대비 상승률(YoY %)입니다. 미국 연방준비제도(FED)가 공식 물가안정 목표(2.0%)를 설정할 때 사용하는 최우선 인플레이션 지표입니다.",
        "chart_type": "single_axis",
        "show_target_line": True,
        "series": [
            {
                "id": "PCE_TOTAL",
                "name": "PCE Total (전년비)",
                "source": "FRED",
                "fred_id": "PCEPI",
                "units": "pc1",
                "axis": "y1",
                "color": "#38bdf8", # Sky Blue
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "PCE_CORE",
                "name": "Core PCE (연준 공식 목표, 전년비)",
                "source": "FRED",
                "fred_id": "PCEPILFE",
                "units": "pc1",
                "axis": "y1",
                "color": "#c084fc", # Purple
                "unit": "%",
                "line_shape": "linear",
                "width": 2.2
            }
        ],
        "y1_label": "PCE 물가 상승률 YoY (%)"
    },
    "Civilian Unemployment Rate": {
        "category": "고용 & 노동시장",
        "description": "미국 16세 이상 민간 노동력 중 실업자 비율(Unemployment Rate)입니다. 경기 후행 지표이나, 경기 침체 시 급격히 상승하며 연준의 완전고용 책무와 직결됩니다.",
        "chart_type": "single_axis",
        "series": [
            {
                "id": "UNRATE",
                "name": "실업률 (Unemployment Rate)",
                "source": "FRED",
                "fred_id": "UNRATE",
                "axis": "y1",
                "color": "#38bdf8", # Sky Blue
                "unit": "%",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "실업률 (%)",
        "show_moving_averages": True
    },
    "Initial Jobless Claims": {
        "category": "고용 & 노동시장",
        "description": "미국 주간 신규 실업수당 청구건수(Initial Claims)입니다. 매주 발표되는 가장 신속한 고용 선행지표로, 노동시장의 둔화 및 해고 증가 추세를 실시간으로 포착합니다.",
        "chart_type": "single_axis",
        "series": [
            {
                "id": "ICSA",
                "name": "신규 실업수당 청구건수 (Initial Claims)",
                "source": "FRED",
                "fred_id": "ICSA",
                "axis": "y1",
                "color": "#fbbf24", # Amber
                "unit": "건",
                "line_shape": "linear",
                "width": 1.8
            }
        ],
        "y1_label": "청구건수 (건)",
        "show_moving_averages": True
    },
    "KOSPI & PER": {
        "category": "한국 증시 & 밸류에이션",
        "description": "한국거래소(KRX)의 코스피(KOSPI) 종합주가지수와 주가수익비율(PER) 추이를 대조합니다. 기업 이익 실적 대비 한국 주식 시장의 저평가/고평가 국면과 바닥권 신호를 포착하는 핵심 지표입니다.",
        "chart_type": "dual_axis",
        "series": [
            {
                "id": "KOSPI",
                "name": "KOSPI 지수",
                "source": "KRX",
                "axis": "y1",
                "color": "#f8fafc", # White/Silver
                "unit": "pt",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "PER",
                "name": "KOSPI PER",
                "source": "KRX",
                "axis": "y2",
                "color": "#ec4899", # Pink
                "unit": "배",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "KOSPI 지수 (pt)",
        "y2_label": "PER (배)",
        "supports_log_scale": True,
        "log_scale_axis": "y1",
        "log_scale_target": "KOSPI"
    },
    "KOSPI & PBR": {
        "category": "한국 증시 & 밸류에이션",
        "description": "한국거래소(KRX)의 코스피(KOSPI) 종합주가지수와 주가순자산비율(PBR) 추이를 대조합니다. 순자산(장부가치) 대비 한국 증시의 역사적 밸류에이션 하단 및 1배(PBR 1.0x)선 지지 여부를 파악할 수 있습니다.",
        "chart_type": "dual_axis",
        "series": [
            {
                "id": "KOSPI",
                "name": "KOSPI 지수",
                "source": "KRX",
                "axis": "y1",
                "color": "#f8fafc", # White/Silver
                "unit": "pt",
                "line_shape": "linear",
                "width": 2.0
            },
            {
                "id": "PBR",
                "name": "KOSPI PBR",
                "source": "KRX",
                "axis": "y2",
                "color": "#06b6d4", # Cyan
                "unit": "배",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "KOSPI 지수 (pt)",
        "y2_label": "PBR (배)",
        "supports_log_scale": True,
        "log_scale_axis": "y1",
        "log_scale_target": "KOSPI"
    }
}
