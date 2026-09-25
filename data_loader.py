import socket
socket.setdefaulttimeout(5.0)

import os
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
import streamlit as st

from config import get_fred_api_key, get_bok_api_key, DEFAULT_START_DATE, INDICATORS, BASE_DIR, DATA_DIR

# FRED API Base URL
FRED_BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_fred_raw(series_id: str, start_date: str = DEFAULT_START_DATE, units: str = None) -> pd.Series:
    """
    FRED API로부터 시계열 데이터를 직접 가져옵니다. (units: pc1 등 변환 지원)
    """
    fred_key = get_fred_api_key()
    if not fred_key:
        return pd.Series(dtype=float)
    
    url = f"{FRED_BASE_URL}?series_id={series_id}&api_key={fred_key}&file_type=json&observation_start={start_date}"
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

@st.cache_data(ttl=1800, show_spinner=False)
def get_fred_series_release_info(series_id: str) -> dict:
    """
    FRED API로부터 시리즈의 최신 공식 발표일(last_updated)과 최신 관측일(observation_end) 메타데이터를 조회합니다.
    """
    fred_key = get_fred_api_key()
    if not fred_key:
        return {}
    url = f"https://api.stlouisfed.org/fred/series?series_id={series_id}&api_key={fred_key}&file_type=json"
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            seriess = data.get("seriess", [])
            if seriess:
                s_info = seriess[0]
                last_updated = s_info.get("last_updated", "")
                obs_end = s_info.get("observation_end", "")
                rel_date = last_updated.split(" ")[0] if last_updated else ""
                return {
                    "release_date": rel_date,
                    "observation_end": obs_end
                }
    except Exception as e:
        print(f"Error fetching FRED series info for {series_id}: {e}")
    return {}

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

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_bok_base_rate(start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    한국은행 ECOS API로부터 한국은행 기준금리(722Y001 / 0101000)를 가져옵니다.
    """
    bok_key = get_bok_api_key()
    if not bok_key:
        return pd.Series(dtype=float)
        
    start_dt = pd.to_datetime(start_date)
    start_month = start_dt.strftime("%Y%m")
    current_month = datetime.now(KST).strftime("%Y%m")
    
    # 722Y001: 한국은행 기준금리 및 여수신금리, 0101000: 한국은행 기준금리
    url = f"https://ecos.bok.or.kr/api/StatisticSearch/{bok_key}/json/kr/1/1000/722Y001/M/{start_month}/{current_month}/0101000"
    
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

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_wti_data(start_date: str = DEFAULT_START_DATE) -> pd.Series:
    """
    WTI 유가 수집: 1990년부터 완벽한 일별 시계열을 제공하는 FRED DCOILWTICO(EIA 현물)를 기반으로,
    최신 데이터는 Yahoo Finance(CL=F 원유 선물)와 스마트 결합하여
    1990년대 걸프전 유가 쇼크부터 어제/오늘 실시간 종가까지 단절 없이 반영합니다.
    """
    s_fred = fetch_fred_raw("DCOILWTICO", start_date)
    s_yahoo = fetch_yahoo_data("CL=F", start_date)
    
    if s_fred.empty and s_yahoo.empty:
        return pd.Series(dtype=float)
    if s_fred.empty:
        combined = s_yahoo
    elif s_yahoo.empty:
        combined = s_fred
    else:
        # Yahoo Finance 최신 데이터를 우선 반영하고, 2000년 이전 데이터는 FRED로 보완
        combined = s_yahoo.combine_first(s_fred)
        
    combined.name = "WTI"
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

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_krx_data(metric_name: str) -> pd.Series:
    """
    KOSPI 지수 및 밸류에이션(PER, PBR) 데이터를 로드합니다.
    사전 구축된 data/krx_kospi_fundamental.csv(2002년~현재)를 기반으로 고속 로드하고,
    최근 30일 데이터는 pykrx(한국거래소)를 통해 실시간 동기화하여 항상 최신 공식 발표치로 갱신합니다.
    """
    csv_file = DATA_DIR / "krx_kospi_fundamental.csv"
    if not csv_file.exists():
        csv_file = BASE_DIR / "data" / "krx_kospi_fundamental.csv"
        
    s_csv = pd.Series(dtype=float)
    if csv_file.exists():
        try:
            df = pd.read_csv(csv_file)
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date").sort_index()
            if metric_name in df.columns:
                s_csv = df[metric_name].dropna()
                s_csv.name = metric_name
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")

    # If s_csv is already up-to-date (within 1 day of today), return immediately to avoid blocking
    if not s_csv.empty:
        last_dt = s_csv.index[-1]
        now_dt = datetime.now(KST).replace(tzinfo=None)
        if hasattr(last_dt, 'tz_localize') and getattr(last_dt, 'tzinfo', None):
            last_dt = last_dt.tz_localize(None)
        days_diff = (now_dt - last_dt).days
        if days_diff <= 1:
            return s_csv.sort_index()

    # pykrx를 통한 최근 30일 실시간 KRX 공식 데이터 동기화 (클라우드 환경 타임아웃 및 차단 대비 방어)
    try:
        from pykrx import stock
        from config import setup_krx_credentials
        setup_krx_credentials()
        now_kst = datetime.now(KST)
        start_recent = (now_kst - pd.Timedelta(days=30)).strftime("%Y%m%d")
        end_recent = now_kst.strftime("%Y%m%d")
        df_krx = stock.get_index_fundamental(start_recent, end_recent, "1001")
        if df_krx is not None and not df_krx.empty:
            df_krx = df_krx.reset_index()
            for col in df_krx.columns:
                if '날짜' in str(col) or 'TRD_DD' in str(col) or 'index' in str(col):
                    df_krx = df_krx.rename(columns={col: "Date"})
                elif '종가' in str(col):
                    df_krx = df_krx.rename(columns={col: "KOSPI"})
            df_krx["Date"] = pd.to_datetime(df_krx["Date"])
            df_krx = df_krx.set_index("Date").sort_index()
            if metric_name in df_krx.columns:
                s_recent = df_krx[metric_name].replace(0, np.nan).dropna()
                s_recent.name = metric_name
                if not s_csv.empty and not s_recent.empty:
                    s_comb = s_recent.combine_first(s_csv)
                    return s_comb.sort_index()
                elif not s_recent.empty:
                    return s_recent.sort_index()
    except Exception as e:
        print(f"pykrx real-time fetch error (falling back to CSV): {e}")

    if not s_csv.empty:
        return s_csv.sort_index()
        
    return pd.Series(dtype=float)

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
        
        if source == "KRX" or s_id in ["KOSPI", "PER", "PBR"]:
            s = fetch_krx_data(s_id)
        elif s_id == "FED_TARGET":
            s = get_fed_target_rate(DEFAULT_START_DATE)
        elif s_id == "BOK_RATE":
            s = fetch_bok_base_rate(DEFAULT_START_DATE)
        elif s_id == "USDKRW":
            s = fetch_usdkrw_data(DEFAULT_START_DATE)
        elif s_id == "WTI":
            s = fetch_wti_data(DEFAULT_START_DATE)
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
        latest_dt = series.index[-1]
        latest_date = latest_dt.strftime("%Y-%m-%d")
        
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
        elif unit == "$/oz":
            val_str = f"${latest_val:,.1f}/oz"
            delta_str = f"{delta:+,.1f}$ ({pct_change:+.2f}%)"
        elif unit == "$":
            val_str = f"${latest_val:,.2f}" if latest_val < 1000 else f"${latest_val:,.0f}"
            delta_str = f"{delta:+,.2f}$ ({pct_change:+.2f}%)" if abs(latest_val) < 1000 else f"{delta:+,.0f}$ ({pct_change:+.2f}%)"
        elif unit == "배":
            val_str = f"{latest_val:.2f}배"
            delta_str = f"{delta:+.2f}배 ({pct_change:+.2f}%)"
        elif unit == "pt":
            val_str = f"{latest_val:,.2f} pt"
            delta_str = f"{delta:+,.2f} pt ({pct_change:+.2f}%)"
        elif unit == "건":
            val_str = f"{int(latest_val):,}건"
            delta_str = f"{int(delta):+,}건 ({pct_change:+.2f}%)"
        else:
            val_str = f"{latest_val:,.2f}"
            delta_str = f"{delta:+,.2f} ({pct_change:+.2f}%)"
            
        # 날짜 및 공식 발표일 명확화 (데이터 대상 기간과 실제 발표일의 혼동 원천 차단)
        name = meta.get("name", col)
        source = meta.get("source", "")
        fred_id = meta.get("fred_id", meta.get("id"))

        # 월별 지표: PPI, CPI, PCE, 실업률, 한국은행 기준금리 또는 매월 1일 관측치
        # (단, 미국 연준 기준금리 FED_TARGET은 일별 데이터이므로 제외)
        is_monthly = any(k in name for k in ["PPI", "CPI", "PCE", "실업률"]) or (col == "BOK_RATE") or latest_date.endswith("-01")
        if col in ["FED_TARGET", "DFEDTAR", "DFEDTARU"]:
            is_monthly = False
        is_weekly = (col == "ICSA")

        if is_monthly:
            period_str = f"{latest_dt.year}년 {latest_dt.month}월 기준"
            rel_date = None
            if "FRED" in source or fred_id:
                rel_info = get_fred_series_release_info(fred_id)
                # 데이터의 마지막 관측일이 FRED의 최신 발표 관측일과 일치할 때만 공식 발표일 표기
                if rel_info and rel_info.get("release_date") and (latest_date == rel_info.get("observation_end")):
                    rel_date = rel_info["release_date"]
            
            if rel_date:
                date_display = f"{period_str} (발표: {rel_date})"
            else:
                date_display = period_str
        elif is_weekly:
            period_str = f"{latest_date} 주간"
            rel_date = None
            if "FRED" in source or fred_id:
                rel_info = get_fred_series_release_info(fred_id)
                if rel_info and rel_info.get("release_date") and (latest_date == rel_info.get("observation_end")):
                    rel_date = rel_info["release_date"]
                    
            if rel_date:
                date_display = f"{period_str} (발표: {rel_date})"
            else:
                date_display = period_str
        else:
            date_display = f"{latest_date} 기준"

        metrics.append({
            "id": col,
            "name": meta.get("name", col),
            "latest_val": val_str,
            "delta": delta_str,
            "date": date_display,
            "color": meta.get("color", "#38bdf8")
        })
        
    return metrics

def get_latest_expected_trading_day(target_date: str = None) -> str:
    """
    가장 최근 거래 완료된 실제 영업일 YYYY-MM-DD 반환.
    - target_date가 전달된 경우: 해당 날짜 기준 (또는 직전 영업일)
    - target_date가 없는 경우: KST 기준 15:45 이전이거나 오늘이 주말/새벽이면 직전 마감 거래일 반환
    """
    from datetime import datetime, timezone, timedelta
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    if target_date:
        try:
            clean_date = str(target_date).replace('-', '')
            dt = datetime.strptime(clean_date, "%Y%m%d").replace(tzinfo=timezone(timedelta(hours=9)))
        except Exception:
            dt = now_kst
    else:
        dt = now_kst

    # 평일 15:45 이후에만 당일 종가 확정
    if dt.weekday() < 5 and (dt.hour > 15 or (dt.hour == 15 and dt.minute >= 45)):
        return dt.strftime("%Y-%m-%d")

    # 장전, 새벽, 주말: 직전 마감 거래일 산출
    if dt.weekday() == 0:    # 월요일 장전 -> 지난주 금요일 (3일 전)
        days_back = 3
    elif dt.weekday() == 6:  # 일요일 -> 지난주 금요일 (2일 전)
        days_back = 2
    elif dt.weekday() == 5:  # 토요일 -> 지난주 금요일 (1일 전)
        days_back = 1
    else:                    # 화~금 장전/새벽 -> 전일 (1일 전)
        days_back = 1

    return (dt - timedelta(days=days_back)).strftime("%Y-%m-%d")
