import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path

from config import INDICATORS, DEFAULT_START_DATE
from data_loader import (
    load_indicator_dataframe,
    get_latest_metrics,
    load_recession_periods
)
from chart_builder import build_chart

# 1. Page Configuration
st.set_page_config(
    page_title="주요 경제 지표 Review & Preview",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom CSS (00 Bookmarks 스타일 완벽 일체화)
st.markdown("""
<style>
    /* 전체 배경 및 텍스트 색상 */
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
    
    /* 메인 콘텐츠 상단 여백 조절 */
    .main .block-container,
    [data-testid="stMainBlockContainer"] {
        padding-top: 2.0rem !important;
        padding-bottom: 2rem !important;
        max-width: 98% !important;
    }
    
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background-color: #1e293b !important;
        border-right: 1px solid #334155 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2 {
        color: #f8fafc !important;
        font-weight: 800 !important;
    }
    
    /* 메인 타이틀 (00 Bookmarks 스타일) */
    h1, .main h1, [data-testid="stHeadingWithActionElements"] h1, .main-title {
        text-align: center !important;
        font-size: 2.0rem !important;
        font-weight: 800 !important;
        line-height: 1.35 !important;
        margin: 0 0 10px 0 !important;
        color: #8AB4F8 !important;
        -webkit-text-fill-color: #8AB4F8 !important;
    }
    
    /* 카드 컨테이너 */
    .metric-card {
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 12px 18px;
        margin-bottom: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    .metric-label {
        font-size: 0.88rem;
        color: #e2e8f0;
        margin-bottom: 2px;
        font-weight: 700;
    }
    .metric-date {
        font-size: 0.76rem;
        color: #94a3b8;
        margin-bottom: 6px;
        font-weight: 500;
    }
    .metric-val {
        font-size: 1.5rem;
        font-weight: 800;
        color: #f8fafc;
    }
    .metric-delta {
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 2px;
    }
    
    /* 구분선 */
    .divider-line {
        border: 0;
        height: 1px;
        background-color: #334155;
        margin: 15px 0 22px 0;
    }
    
    /* Buttons styling (45 RealEstate 테마 일치) */
    div.stButton > button {
        border-radius: 6px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }

    /* 사이드바 가로 버튼 간격 축소 */
    section[data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
        gap: 6px !important;
    }

    /* 사이드바 버튼 높이 및 텍스트 레이아웃 (45 RealEstate 기준 일치) */
    section[data-testid="stSidebar"] div.stButton > button {
        border-radius: 6px !important;
        font-weight: 700 !important;
        padding-left: 2px !important;
        padding-right: 2px !important;
        padding-top: 4px !important;
        padding-bottom: 4px !important;
        min-height: 36px !important;
        height: 36px !important;
        white-space: nowrap !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    /* 사이드바 버튼 내부 텍스트 줄바꿈 방지 및 크기 일치 */
    section[data-testid="stSidebar"] div.stButton > button p {
        white-space: nowrap !important;
        overflow: visible !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        line-height: 1 !important;
        margin: 0 !important;
        padding: 0 !important;
        display: inline-block !important;
    }

    /* 빠른 선택 버튼 스타일링 */
    div[data-testid="stHorizontalBlock"] button {
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.88rem;
        transition: all 0.2s;
    }
    
    /* 라디오 버튼 텍스트 가독성 */
    div[data-testid="stRadio"] label {
        color: #e2e8f0 !important;
        font-size: 0.95rem;
        padding: 6px 0;
    }

    /* =========================================================
       사이드바 접기(<<) 및 펼치기(>>) 버튼 항상 표시 및 시인성/대비 강화
       ========================================================= */
    /* 1. 사이드바가 열려 있을 때 접기 버튼 (<<) 상시 표시 */
    [data-testid="stSidebarCollapseButton"] {
        visibility: visible !important;
        opacity: 1 !important;
        display: inline-flex !important;
    }
    
    [data-testid="stSidebarCollapseButton"] button {
        visibility: visible !important;
        opacity: 1 !important;
        background-color: #1e293b !important;       /* 진한 네이비 배경 */
        border: 1.5px solid #38bdf8 !important;     /* 선명한 스카이블루 테두리로 상자 명확화 */
        border-radius: 8px !important;
        width: 38px !important;
        height: 38px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
        transition: all 0.2s ease !important;
    }
    
    /* 상자 내부의 << 아이콘(Material Icon span/svg/문자)을 순백색으로 강제하여 상자와 극명한 대비 구현 */
    [data-testid="stSidebarCollapseButton"] button *,
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapseButton"] svg {
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
        font-weight: 700 !important;
    }
    
    /* 호버(PC) 및 터치 시 반전 효과 */
    [data-testid="stSidebarCollapseButton"] button:hover {
        background-color: #38bdf8 !important;
        border-color: #38bdf8 !important;
    }
    [data-testid="stSidebarCollapseButton"] button:hover * {
        color: #0f172a !important;
        fill: #0f172a !important;
    }

    /* 2. 사이드바 헤더 영역 패딩 및 정렬 보정 */
    [data-testid="stSidebarHeader"] {
        padding-top: 0.5rem !important;
        padding-bottom: 0.5rem !important;
    }

    /* 3. 사이드바가 닫혔을 때 다시 여는 버튼 (>>) 시인성 강화 */
    [data-testid="stSidebarCollapsedControl"] {
        visibility: visible !important;
        opacity: 1 !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button {
        background-color: #1e293b !important;
        border: 1.5px solid #38bdf8 !important;
        border-radius: 8px !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4), 0 0 6px rgba(56, 189, 248, 0.2) !important;
    }
    
    [data-testid="stSidebarCollapsedControl"] button *,
    [data-testid="stSidebarCollapsedControl"] span,
    [data-testid="stSidebarCollapsedControl"] [data-testid="stIconMaterial"],
    [data-testid="stSidebarCollapsedControl"] svg {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
        opacity: 1 !important;
        visibility: visible !important;
        font-size: 1.35rem !important;
    }

    /* 다운로드 버튼 공통 통일 스타일 */
    div[data-testid="stDownloadButton"] > button,
    .stDownloadButton > button {
        background-color: #334155 !important;
        color: #f8fafc !important;
        border: 1px solid #475569 !important;
        border-radius: 6px !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        height: 38px !important;
        min-height: 38px !important;
        max-height: 38px !important;
        line-height: 36px !important;
        padding: 0 16px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        transition: all 0.2s ease-in-out !important;
        box-sizing: border-box !important;
    }
    div[data-testid="stDownloadButton"] > button:hover,
    .stDownloadButton > button:hover {
        background-color: #475569 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
        box-shadow: 0 0 10px rgba(56, 189, 248, 0.25) !important;
    }
    div[data-testid="stDownloadButton"] > button:active,
    .stDownloadButton > button:active {
        background-color: #1e293b !important;
        border-color: #0284c7 !important;
    }
    div[data-testid="stDownloadButton"] > button p,
    div[data-testid="stDownloadButton"] > button span,
    .stDownloadButton > button p,
    .stDownloadButton > button span {
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        color: inherit !important;
        line-height: inherit !important;
        margin: 0 !important;
        padding: 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. Session State 초기화
today = datetime.now().date()
max_start = datetime.strptime(DEFAULT_START_DATE, "%Y-%m-%d").date()

if "selected_indicator" not in st.session_state:
    st.session_state.selected_indicator = list(INDICATORS.keys())[0]

if "range_choice" not in st.session_state:
    st.session_state.range_choice = "MAX"

if "start_date" not in st.session_state:
    st.session_state.start_date = max_start

if "end_date" not in st.session_state:
    st.session_state.end_date = today

# 빠른 선택 버튼 클릭 핸들러
def set_quick_range(choice: str):
    st.session_state.range_choice = choice
    st.session_state.end_date = today
    if choice == "1Y":
        st.session_state.start_date = max(max_start, today - timedelta(days=365))
    elif choice == "5Y":
        st.session_state.start_date = max(max_start, today - timedelta(days=365 * 5))
    elif choice == "10Y":
        st.session_state.start_date = max(max_start, today - timedelta(days=365 * 10))
    elif choice == "MAX":
        st.session_state.start_date = max_start

# 4. 왼쪽 패널 (사이드바)
with st.sidebar:
    st.markdown("<h2 style='font-size: 1.4rem; margin-bottom: 8px;'>📌 주요 경제 지표</h2>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 0.85rem; color: #94a3b8; margin-bottom: 18px;'>조회할 경제 지표를 선택하세요.</div>", unsafe_allow_html=True)
    
    indicator_options = list(INDICATORS.keys())
    
    st.radio(
        label="지표 선택",
        options=indicator_options,
        key="selected_indicator",
        label_visibility="collapsed"
    )
    
    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # Update / 데이터 최신화 버튼
    col_up1, col_up2 = st.columns([1, 1])
    with col_up1:
        if st.button("🔄 Update", use_container_width=True, help="최신 데이터를 다시 수집하고 캐시를 갱신합니다."):
            st.cache_data.clear()
            st.toast("데이터 캐시를 갱신하고 최신 데이터를 수집했습니다!", icon="✅")
            st.rerun()
    with col_up2:
        if st.button("🔍 조회", type="primary", use_container_width=True, help="선택한 조건으로 다시 조회합니다."):
            st.rerun()
            
    st.markdown("<hr style='border: 0; height: 1px; background-color: #334155; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # 지표 정보 안내 카드
    current_config = INDICATORS[st.session_state.selected_indicator]
    st.markdown(f"<div style='font-size: 0.88rem; font-weight: 700; color: #38bdf8; margin-bottom: 6px;'>[ {current_config.get('category', '지표 정보')} ]</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='font-size: 0.83rem; color: #cbd5e1; line-height: 1.5; margin-bottom: 12px;'>{current_config.get('description', '')}</div>", unsafe_allow_html=True)
    
    # 출처 안내
    st.markdown("""
    <div style='background-color: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 10px; font-size: 0.78rem; color: #94a3b8;'>
        <b>데이터 출처:</b><br>
        • 미국 연준 FRED (St. Louis Fed)<br>
        • 한국은행 ECOS Open API<br>
        • 한국거래소 KRX (Korea Exchange)<br>
        • Yahoo Finance
    </div>
    """, unsafe_allow_html=True)

# 5. 오른쪽 메인 영역

# A. 타이틀 영역 (00 Bookmarks 스타일 준수)
st.markdown("<h1 class='main-title' style='text-align: center; font-size: 2.0rem !important; font-weight: 800 !important; color: #8AB4F8 !important; -webkit-text-fill-color: #8AB4F8 !important; margin: 0 0 10px 0;'><span style='color: #8AB4F8 !important; -webkit-text-fill-color: #8AB4F8 !important;'>주요 경제 지표 Review & Preview</span></h1>", unsafe_allow_html=True)
st.markdown("<hr class='divider-line'>", unsafe_allow_html=True)

# B. 차트 영역 상단: 차트 명칭 & 기간 설정
col_title, col_periods = st.columns([1.1, 1.3], vertical_alignment="center")

with col_title:
    st.markdown(f"<div style='font-size: 1.35rem; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;'>📈 {st.session_state.selected_indicator}</div>", unsafe_allow_html=True)

with col_periods:
    # 빠른 선택 버튼 4개 (1Y, 5Y, 10Y, MAX) + 캘린더 시작일/종료일
    btn_col1, btn_col2, btn_col3, btn_col4, date_col1, date_col2 = st.columns([1, 1, 1, 1.2, 2.2, 2.2])
    
    with btn_col1:
        is_1y = (st.session_state.range_choice == "1Y")
        if st.button("1Y", type="primary" if is_1y else "secondary", use_container_width=True):
            set_quick_range("1Y")
            st.rerun()
            
    with btn_col2:
        is_5y = (st.session_state.range_choice == "5Y")
        if st.button("5Y", type="primary" if is_5y else "secondary", use_container_width=True):
            set_quick_range("5Y")
            st.rerun()
            
    with btn_col3:
        is_10y = (st.session_state.range_choice == "10Y")
        if st.button("10Y", type="primary" if is_10y else "secondary", use_container_width=True):
            set_quick_range("10Y")
            st.rerun()
            
    with btn_col4:
        is_max = (st.session_state.range_choice == "MAX")
        if st.button("MAX", type="primary" if is_max else "secondary", use_container_width=True):
            set_quick_range("MAX")
            st.rerun()
            
    with date_col1:
        picked_start = st.date_input(
            "시작일",
            value=st.session_state.start_date,
            min_value=max_start,
            max_value=today,
            label_visibility="collapsed"
        )
        if picked_start != st.session_state.start_date:
            st.session_state.start_date = picked_start
            st.session_state.range_choice = "CUSTOM"
            st.rerun()
            
    with date_col2:
        picked_end = st.date_input(
            "종료일",
            value=st.session_state.end_date,
            min_value=max_start,
            max_value=today,
            label_visibility="collapsed"
        )
        if picked_end != st.session_state.end_date:
            st.session_state.end_date = picked_end
            st.session_state.range_choice = "CUSTOM"
            st.rerun()

# C. 옵션 컨트롤 바 (경기침체 음영, 로그스케일, 스프레드 등)
opt_col1, opt_col2, opt_col3, opt_col4 = st.columns([1.5, 1.5, 1.5, 3.5])

with opt_col1:
    show_recession = st.checkbox("경기침체 음영 (NBER)", value=True, help="미국 경기침체 공식 구간(NBER)을 회색 음영으로 표시합니다.")
    
supports_log = current_config.get("supports_log_scale", False)
with opt_col2:
    if supports_log:
        target_name = current_config.get("log_scale_target")
        if not target_name:
            if "Bitcoin" in st.session_state.selected_indicator:
                target_name = "Bitcoin"
            elif "SOX" in st.session_state.selected_indicator:
                target_name = "SOX"
            elif "KOSPI" in st.session_state.selected_indicator:
                target_name = "KOSPI"
            else:
                target_name = "S&P 500"
        use_log = st.checkbox(f"로그 스케일 ({target_name})", value=False, help=f"{target_name} 축을 로그 스케일로 표시합니다.")
    else:
        use_log = False

has_spread_option = current_config.get("show_spread_option", False)
with opt_col3:
    if has_spread_option:
        show_spread = st.checkbox("한미 금리차 (Spread)", value=True, help="미국 기준금리 - 한국 기준금리 스프레드 선을 추가로 표시합니다.")
    else:
        show_spread = False
        
has_ma = current_config.get("show_moving_averages", False)
with opt_col4:
    if has_ma:
        show_ma = st.checkbox("이동평균선 (50일/200일)", value=False, help="50일 및 200일 이동평균선을 함께 표시합니다.")
    else:
        show_ma = False

# D. 데이터 로딩 및 최신 지표 요약 카드
start_str = st.session_state.start_date.strftime("%Y-%m-%d")
end_str = st.session_state.end_date.strftime("%Y-%m-%d")

with st.spinner("데이터를 조회하고 있습니다..."):
    df_data = load_indicator_dataframe(
        indicator_name=st.session_state.selected_indicator,
        start_date=start_str,
        end_date=end_str
    )
    recession_periods = load_recession_periods(DEFAULT_START_DATE) if show_recession else []

if not df_data.empty:
    metrics = get_latest_metrics(df_data, st.session_state.selected_indicator)
    if metrics:
        metric_cols = st.columns(len(metrics))
        for idx, m in enumerate(metrics):
            with metric_cols[idx]:
                delta_color = "#4ade80" if ("+" in m["delta"] and "%" not in m["latest_val"]) or ("+" in m["delta"] and "환율" in m["name"]) else ("#f87171" if "-" in m["delta"] else "#94a3b8")
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">{m['name']}</div>
                    <div class="metric-date">📅 {m['date']}</div>
                    <div class="metric-val" style="color: {m['color']};">{m['latest_val']}</div>
                    <div class="metric-delta" style="color: {delta_color};">직전 변동: {m['delta']}</div>
                </div>
                """, unsafe_allow_html=True)
                
    # E. 차트 렌더링
    fig = build_chart(
        df=df_data,
        indicator_name=st.session_state.selected_indicator,
        show_recession=show_recession,
        recession_periods=recession_periods,
        use_log_scale=use_log,
        show_ma=show_ma,
        show_spread=show_spread
    )
    
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "scrollZoom": True})
else:
    st.warning("선택한 기간에 해당하는 데이터가 없거나 수집 중 오류가 발생했습니다. 잠시 후 'Update' 버튼을 눌러주세요.")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #64748b; font-size: 0.8rem; margin-top: 8px; margin-bottom: 24px; line-height: 1.6;'>⚠️ 본 서비스에서 제공하는 모든 정보는 투자 참고용이며, 투자의 최종 결정과 책임은 투자자 본인에게 있습니다.</div>", unsafe_allow_html=True)
