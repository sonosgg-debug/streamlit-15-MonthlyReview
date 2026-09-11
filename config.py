import os
import re
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
API_KEY_DIR = BASE_DIR.parent / "00 API Key"

def get_api_key(service_name: str) -> str:
    """
    서비스별 API 키를 Streamlit Secrets, 환경변수, 또는 로컬 파일에서 안전하게 로드합니다.
    """
    # 1. Streamlit Secrets (Streamlit Cloud 배포 환경)
    try:
        import streamlit as st
        key_name = f"{service_name.upper()}_API_KEY"
        if hasattr(st, "secrets") and key_name in st.secrets:
            return str(st.secrets[key_name]).strip()
    except Exception:
        pass

    # 2. OS 환경 변수
    env_key = os.getenv(f"{service_name.upper()}_API_KEY")
    if env_key:
        return env_key.strip()
    
    # 3. 로컬 00 API Key 디렉토리 탐색 (로컬 PC 실행 환경)
    if API_KEY_DIR.exists():
        if service_name.upper() == "FRED":
            fred_file = API_KEY_DIR / "FRED StLouis ID&PW.txt"
            if fred_file.exists():
                try:
                    text = fred_file.read_text(encoding="utf-8")
                    match = re.search(r"API\s*Key\s*:\s*([a-zA-Z0-9]+)", text, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
                except Exception:
                    pass
        elif service_name.upper() in ["BOK", "ECOS"]:
            bok_file = API_KEY_DIR / "BOK ID&PW.txt"
            if bok_file.exists():
                try:
                    text = bok_file.read_text(encoding="utf-8")
                    match = re.search(r"API\s*key\s*:\s*([a-zA-Z0-9]+)", text, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
                except Exception:
                    pass
                    
    return ""

FRED_API_KEY = get_api_key("FRED")
BOK_API_KEY = get_api_key("BOK")

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
    "US Dollar Index": {
        "category": "통화 & 외환",
        "description": "주요 6개국 통화 대비 미국 달러화의 가치를 나타내는 달러 인덱스(DXY)입니다. 글로벌 유동성 및 안전자산 선호 심리, 원자재 가격과 밀접하게 연동됩니다.",
        "chart_type": "single_axis",
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
            }
        ],
        "y1_label": "달러 인덱스 (pt)",
        "show_moving_averages": True
    },
    "USD/KRW Exchange Rate": {
        "category": "통화 & 외환",
        "description": "달러 대비 원화 환율(USD/KRW)의 추이입니다. 한국의 수출입 경쟁력, 외국인 자금 흐름, 국가 신용위험을 반영하는 대표적인 환율 지표입니다.",
        "chart_type": "single_axis",
        "series": [
            {
                "id": "USDKRW",
                "name": "USD/KRW 환율",
                "source": "FRED",
                "fred_id": "DEXKOUS",
                "axis": "y1",
                "color": "#2dd4bf", # Teal
                "unit": "원",
                "line_shape": "linear",
                "width": 2.0
            }
        ],
        "y1_label": "원/달러 환율 (KRW)",
        "show_moving_averages": True
    },
    "Crude Oil Prices: (WTI)": {
        "category": "원자재 & 에너지",
        "description": "서부 텍사스산 원유(WTI) 현물 가격 추이입니다. 글로벌 에너지 비용, 공급망 물가 및 인플레이션 압력을 예측하는 대표적인 원자재 선행지표입니다.",
        "chart_type": "single_axis",
        "series": [
            {
                "id": "WTI",
                "name": "WTI 유가 (Crude Oil)",
                "source": "FRED",
                "fred_id": "DCOILWTICO",
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
    "Producer Price Index (PPI) Total & Core": {
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
    "Consumer Price Index (CPI) Total & Core": {
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
    "Personal Consumption Expenditures (PCE) Total & Core": {
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
    }
}
