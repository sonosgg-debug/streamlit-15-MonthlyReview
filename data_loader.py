import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
import streamlit as st

from config import FRED_API_KEY, BOK_API_KEY, DEFAULT_START_DATE, INDICATORS

# FRED API Base URL
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_fred_raw(series_id: str, start_date: str = DEFAULT_START_DATE, units: str = None) -> pd.Series:
    """
    FRED API로부터 시계열 데이터를 직접 가져옵니다. (units: pc1 등 변환 지원)
    """
    if not FRED_API_KEY:
        return pd.Series(dtype=float)
    
    url = f"{FRED_BASE_URL}?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json&observation_start={start_date}"
    if units:
        url += f"&units={units}"
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return pd.Series(dtype=float)
        data = resp.json()
        observations = data.get("observations", [])
        if not observations:
            return pd.Series(dtype=float)
        
        dates = []
        values = []
        for obs in observations:
            val_str = obs.get("value")
            if val_str and val_str != ".":
                try:
                    values.append(float(val_str))
                    dates.append(pd.to_datetime(obs["date"]))
                except ValueError:
                    continue
        
        series = pd.Series(data=values, index=dates, name=series_id)
        series = series[~series.index.duplicated(keep="last")]
        return series.sort_index()
    except Exception as e:
        print(f"Error fetching FRED series {series_id}: {e}")
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600, show_spinner=False)
def get_fed_target_rate(start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    과거 목표금리(DFEDTAR)와 현재 상한 목표금리(DFEDTARU)를 결합하여 일관된 FED Target Rate 생성
    """
    s_upper = fetch_fred_raw("DFEDTARU", start_date)
    s_past = fetch_fred_raw("DFEDTAR", start_date)
    
    if s_upper.empty and s_past.empty:
        # Fallback to FEDFUNDS
        return fetch_fred_raw("FEDFUNDS", start_date)
    
    if s_upper.empty:
        combined = s_past
    elif s_past.empty:
        combined = s_upper
    else:
        # Combine upper first, then fill with past
        combined = s_upper.combine_first(s_past)
        
    combined.name = "FED_TARGET"
    return combined.sort_index()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_bok_base_rate(start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    한국은행 ECOS API로부터 한국은행 기준금리(722Y001 / 0101000)를 가져옵니다.
    """
    if not BOK_API_KEY:
        return pd.Series(dtype=float)
        
    start_dt = pd.to_datetime(start_date)
    start_month = start_dt.strftime("%Y%m")
    current_month = datetime.now().strftime("%Y%m")
    
    # 722Y001: 한국은행 기준금리 및 여수신금리, 0101000: 한국은행 기준금리
    url = f"https://ecos.bok.or.kr/api/StatisticSearch/{BOK_API_KEY}/json/kr/1/1000/722Y001/M/{start_month}/{current_month}/0101000"
    
    try:
        resp = requests.get(url, timeout=12)
        if resp.status_code != 200:
            return pd.Series(dtype=float)
        data = resp.json()
        if "StatisticSearch" not in data or "row" not in data["StatisticSearch"]:
            return pd.Series(dtype=float)
            
        rows = data["StatisticSearch"]["row"]
        dates = []
        values = []
        for r in rows:
            try:
                # TIME is YYYYMM format
                dt = pd.to_datetime(r["TIME"], format="%Y%m")
                val = float(r["DATA_VALUE"])
                dates.append(dt)
                values.append(val)
            except Exception:
                continue
                
        series = pd.Series(data=values, index=dates, name="BOK_RATE")
        series = series[~series.index.duplicated(keep="last")]
        return series.sort_index()
    except Exception as e:
        print(f"Error fetching BOK base rate: {e}")
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_yahoo_data(ticker: str, start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    Yahoo Finance로부터 일별 종가 데이터를 가져옵니다.
    """
    try:
        df = yf.download(ticker, start=start_date, progress=False)
        if df.empty:
            return pd.Series(dtype=float)
        
        # Flatten MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        if "Close" in df.columns:
            s = df["Close"].dropna()
            # timezone unlocalize if needed
            if hasattr(s.index, "tz") and s.index.tz is not None:
                s.index = s.index.tz_localize(None)
            s.name = ticker
            return s.sort_index()
        return pd.Series(dtype=float)
    except Exception as e:
        print(f"Error fetching Yahoo ticker {ticker}: {e}")
        return pd.Series(dtype=float)

@st.cache_data(ttl=3600, show_spinner=False)
def load_recession_periods(start_date: str = DEFAULT_START_DATE):
    """
    FRED USREC(NBER 경기침체 지표)를 분석하여 [시작일, 종료일] 구간 리스트 반환
    """
    usrec = fetch_fred_raw("USREC", start_date)
    if usrec.empty:
        return []
    
    # 1인 기간 찾기
    recession_dates = usrec[usrec == 1].index
    if len(recession_dates) == 0:
        return []
        
    periods = []
    start_p = recession_dates[0]
    prev_p = recession_dates[0]
    
    for dt in recession_dates[1:]:
        # 월별 데이터이므로 간격이 45일 이상이면 새로운 침체 구간으로 인식
        if (dt - prev_p).days > 45:
            # 이전 침체구간 종료 (해당 월의 말일 부근까지)
            end_p = prev_p + pd.offsets.MonthEnd(1)
            periods.append((start_p.strftime("%Y-%m-%d"), end_p.strftime("%Y-%m-%d")))
            start_p = dt
        prev_p = dt
        
    end_p = prev_p + pd.offsets.MonthEnd(1)
    periods.append((start_p.strftime("%Y-%m-%d"), end_p.strftime("%Y-%m-%d")))
    return periods

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_usdkrw_data(start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    원/달러 환율 수집: 1990년부터 완벽한 일별 시계열을 제공하는 FRED DEXKOUS를 기반으로,
    최신 데이터는 Yahoo Finance(KRW=X)와 결합합니다.
    (1997~1998년 IMF 아시아 외환위기 환율 폭등 구간 완벽 지원)
    """
    s_fred = fetch_fred_raw("DEXKOUS", start_date)
    s_yahoo = fetch_yahoo_data("KRW=X", start_date)
    
    if s_fred.empty and s_yahoo.empty:
        return pd.Series(dtype=float)
    if s_fred.empty:
        combined = s_yahoo
    elif s_yahoo.empty:
        combined = s_fred
    else:
        # Yahoo 최신 데이터를 우선하고, 2003년 이전(1990~2003)은 FRED로 채움
        combined = s_yahoo.combine_first(s_fred)
        
    combined.name = "USDKRW"
    return combined.sort_index()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ppi_total_data(start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    공식 헤드라인 생산자물가지수(PPI Final Demand YoY %):
    2009년 11월 이후는 인베스팅닷컴 공식 헤드라인인 PPIFIS(pc1, 최종 5.41%),
    2009년 이전은 장기 공식 Finished Goods PPI인 WPSFD49207(pc1)를 스마트 결합하여
    1990년부터 어제(9월 10일) 발표치까지 단절 없는 완벽한 공식 시계열 생성.
    """
    s_new = fetch_fred_raw("PPIFIS", start_date, units="pc1")
    s_old = fetch_fred_raw("WPSFD49207", start_date, units="pc1")
    
    if s_new.empty and s_old.empty:
        return pd.Series(dtype=float)
    if s_new.empty:
        combined = s_old
    elif s_old.empty:
        combined = s_new
    else:
        combined = s_new.combine_first(s_old)
        
    combined.name = "PPI_TOTAL"
    return combined.sort_index()

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ppi_core_data(start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    공식 근원 생산자물가지수(Core PPI Final Demand YoY %):
    인베스팅닷컴 및 시장 공식 지표인 PPIFES(최종수요 식품·에너지 제외, 최신 4.62%)를 기본으로,
    2010년 이전은 과거 장기 공식 Core PPI인 WPSFD4131(pc1)를 스마트 결합하여
    1990년부터 어제 발표치(4.6%)까지 단절 없는 완벽한 공식 시계열 생성.
    """
    s_new = fetch_fred_raw("PPIFES", start_date, units="pc1")
    s_old = fetch_fred_raw("WPSFD4131", start_date, units="pc1")
    
    if s_new.empty and s_old.empty:
        return pd.Series(dtype=float)
    if s_new.empty:
        combined = s_old
    elif s_old.empty:
        combined = s_new
    else:
        combined = s_new.combine_first(s_old)
        
    combined.name = "PPI_CORE"
    return combined.sort_index()

def load_indicator_dataframe(indicator_name: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    선택된 경제 지표에 필요한 모든 시리즈를 수집하고 통합된 일별 DataFrame으로 반환합니다.
    """
    config = INDICATORS.get(indicator_name)
    if not config:
        return pd.DataFrame()
        
    series_list = config.get("series", [])
    collected = {}
    
    for s_meta in series_list:
        s_id = s_meta["id"]
        source = s_meta.get("source")
        
        if s_id == "FED_TARGET":
            s = get_fed_target_rate(DEFAULT_START_DATE)
        elif s_id == "BOK_RATE":
            s = fetch_bok_base_rate(DEFAULT_START_DATE)
        elif s_id == "USDKRW":
            s = fetch_usdkrw_data(DEFAULT_START_DATE)
        elif s_id == "PPI_TOTAL":
            s = fetch_ppi_total_data(DEFAULT_START_DATE)
        elif s_id == "PPI_CORE":
            s = fetch_ppi_core_data(DEFAULT_START_DATE)
        elif source == "FRED":
            fred_id = s_meta.get("fred_id", s_id)
            fred_units = s_meta.get("units", None)
            s = fetch_fred_raw(fred_id, DEFAULT_START_DATE, units=fred_units)
        elif source == "YAHOO":
            ticker = s_meta.get("ticker", s_id)
            s = fetch_yahoo_data(ticker, DEFAULT_START_DATE)
        else:
            s = pd.Series(dtype=float)
            
        if s is not None and not s.empty:
            collected[s_id] = s
            
    if not collected:
        return pd.DataFrame()
        
    df = pd.DataFrame(collected)
    
    # 공통 날짜 인덱스로 결합 후 일별 캘린더 생성
    min_date = df.index.min()
    max_date = df.index.max()
    full_idx = pd.date_range(start=min_date, end=max_date, freq="D")
    df = df.reindex(full_idx)
    
    # 각 컬럼별로 최초 유효 관측일 이후에만 순방향 채우기(ffill) 적용
    # (한국은행 기준금리처럼 1999년 5월 도입 이전 데이터는 절대 bfill하지 않고 NaN 유지)
    for col in df.columns:
        first_valid = df[col].first_valid_index()
        if first_valid is not None:
            df.loc[first_valid:, col] = df.loc[first_valid:, col].ffill()
            df.loc[:first_valid - pd.Timedelta(days=1), col] = np.nan
    
    # 사용자가 요청한 기간(start_date ~ end_date)으로 슬라이싱
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # 시간 오차 방지를 위해 날짜 범위 필터링
    mask = (df.index >= start_dt) & (df.index <= end_dt)
    filtered_df = df.loc[mask].copy()
    filtered_df.index.name = "Date"
    
    return filtered_df

def get_latest_metrics(df: pd.DataFrame, indicator_name: str):
    """
    각 시리즈별 최신값 및 전일(또는 1개월 전) 대비 증감률(Delta)을 계산합니다.
    """
    metrics = []
    config = INDICATORS.get(indicator_name, {})
    series_configs = {s["id"]: s for s in config.get("series", [])}
    
    for col in df.columns:
        if col not in series_configs:
            continue
        meta = series_configs[col]
        series = df[col].dropna()
        if len(series) == 0:
            continue
            
        latest_val = series.iloc[-1]
        latest_date = series.index[-1].strftime("%Y-%m-%d")
        
        # 전일 또는 1주/1달 전 값 비교
        if len(series) >= 2:
            prev_val = series.iloc[-2]
            delta = latest_val - prev_val
            pct_change = (delta / abs(prev_val) * 100) if prev_val != 0 else 0
        else:
            delta = 0.0
            pct_change = 0.0
            
        unit = meta.get("unit", "")
        # 포맷팅
        if unit == "%" or unit == "%p":
            val_str = f"{latest_val:.2f}%"
            delta_str = f"{delta:+.2f}%p"
        elif unit == "원":
            val_str = f"{latest_val:,.1f}원"
            delta_str = f"{delta:+,.1f}원 ({pct_change:+.2f}%)"
        elif unit == "$":
            val_str = f"${latest_val:,.2f}"
            delta_str = f"{delta:+,.2f}$ ({pct_change:+.2f}%)"
        elif unit == "건":
            val_str = f"{int(latest_val):,}건"
            delta_str = f"{int(delta):+,}건 ({pct_change:+.2f}%)"
        else:
            val_str = f"{latest_val:,.2f}"
            delta_str = f"{delta:+,.2f} ({pct_change:+.2f}%)"
            
        # 월별 지표의 경우 '2026.08월 발표치'처럼 직관적으로 표시
        is_monthly = any(k in meta.get("name", "") for k in ["PPI", "CPI", "PCE", "실업률"])
        if is_monthly and latest_date.endswith("-01"):
            date_display = f"{latest_date[:7]}월 발표치"
        else:
            date_display = latest_date

        metrics.append({
            "id": col,
            "name": meta.get("name", col),
            "latest_val": val_str,
            "delta": delta_str,
            "date": date_display,
            "color": meta.get("color", "#38bdf8")
        })
        
    return metrics
