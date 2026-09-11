import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

from config import INDICATORS

def build_chart(
    df: pd.DataFrame,
    indicator_name: str,
    show_recession: bool = True,
    recession_periods: list = None,
    use_log_scale: bool = False,
    show_ma: bool = False,
    show_spread: bool = False
) -> go.Figure:
    """
    선택된 경제 지표와 옵션에 맞추어 고품질 인터랙티브 Plotly 차트를 생성합니다.
    """
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="조회할 데이터가 없습니다.",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=18, color="#94a3b8")
        )
        fig.update_layout(
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a"
        )
        return fig

    config = INDICATORS.get(indicator_name, {})
    chart_type = config.get("chart_type", "single_axis")
    is_dual = (chart_type == "dual_axis")
    
    # Create Figure
    if is_dual:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
    else:
        fig = go.Figure()
        
    series_configs = config.get("series", [])
    
    # 1. Plot Series Lines
    for s_meta in series_configs:
        s_id = s_meta["id"]
        if s_id not in df.columns:
            continue
            
        s_data = df[s_id].dropna()
        if s_data.empty:
            continue
            
        is_secondary = (is_dual and s_meta.get("axis") == "y2")
        unit = s_meta.get("unit", "")
        
        # Hover format based on unit
        if unit == "%" or unit == "%p":
            hover_fmt = ":.2f" + unit
        elif unit == "원":
            hover_fmt = ":,.1f원"
        elif unit == "$":
            hover_fmt = ":$,.2f"
        elif unit == "건":
            hover_fmt = ":,.0f건"
        else:
            hover_fmt = ":,.2f " + unit
            
        trace = go.Scatter(
            x=s_data.index,
            y=s_data.values,
            name=s_meta.get("name", s_id),
            mode="lines",
            line=dict(
                color=s_meta.get("color", "#38bdf8"),
                width=s_meta.get("width", 2.0),
                shape=s_meta.get("line_shape", "linear")
            ),
            hovertemplate=f"<b>{s_meta.get('name', s_id)}</b>: %{{y{hover_fmt}}}<extra></extra>"
        )
        
        if is_dual:
            fig.add_trace(trace, secondary_y=is_secondary)
        else:
            fig.add_trace(trace)
            
        # 이동평균선 옵션 (show_ma == True이고 단일 축인 경우)
        if show_ma and not is_dual and len(s_data) > 50:
            ma50 = s_data.rolling(50).mean()
            ma200 = s_data.rolling(200).mean()
            
            fig.add_trace(go.Scatter(
                x=ma50.index,
                y=ma50.values,
                name=f"{s_meta.get('name', s_id)} (50일 이평선)",
                mode="lines",
                line=dict(color="#fb923c", width=1.2, dash="dot"),
                hovertemplate=f"50일 이평: %{{y{hover_fmt}}}<extra></extra>"
            ))
            
            if len(s_data) > 200:
                fig.add_trace(go.Scatter(
                    x=ma200.index,
                    y=ma200.values,
                    name=f"{s_meta.get('name', s_id)} (200일 이평선)",
                    mode="lines",
                    line=dict(color="#ec4899", width=1.4, dash="dash"),
                    hovertemplate=f"200일 이평: %{{y{hover_fmt}}}<extra></extra>"
                ))

    # 2. 한미 금리차(FED - BOK) 스프레드 표시 옵션
    if show_spread and "FED_TARGET" in df.columns and "BOK_RATE" in df.columns:
        spread = (df["FED_TARGET"] - df["BOK_RATE"]).dropna()
        if not spread.empty:
            fig.add_trace(go.Scatter(
                x=spread.index,
                y=spread.values,
                name="한미 금리차 (미국 - 한국)",
                mode="lines",
                line=dict(color="#c084fc", width=1.5, dash="dashdot"),
                hovertemplate="한미 금리차: %{y:+.2f}%p<extra></extra>"
            ))
            # 0% 기준선 추가
            fig.add_hline(y=0, line_dash="solid", line_color="#94a3b8", line_width=1, opacity=0.7)

    # 3. 장단기 금리차 역전(0% 이하) 및 기준선 강조
    if config.get("highlight_zero_line", False) and "T10Y2Y" in df.columns:
        fig.add_hline(
            y=0,
            line_dash="dash",
            line_color="#f43f5e",
            line_width=1.5,
            annotation_text="0% 역전 기준선 (Inversion Threshold)",
            annotation_position="bottom right",
            annotation_font=dict(color="#f43f5e", size=11)
        )
        
        # 금리차 0 이하 역전 구간을 시각적으로 채우기
        spread_data = df["T10Y2Y"].dropna()
        if not spread_data.empty:
            # 0 이하인 부분 음영 처리 (시각적 경고)
            fig.add_trace(go.Scatter(
                x=spread_data.index,
                y=np.where(spread_data < 0, spread_data, 0),
                fill="tozeroy",
                fillcolor="rgba(244, 63, 94, 0.25)",
                mode="none",
                name="금리 역전 구간 (<0%p)",
                showlegend=True,
                hoverinfo="skip"
            ))

    # 3-2. 인플레이션 목표치(2.0%) 및 0% 기준선 표시 (CPI, PPI, PCE)
    if config.get("show_target_line", False):
        fig.add_hline(
            y=2.0,
            line_dash="dash",
            line_color="#facc15",
            line_width=1.5,
            annotation_text="연준 물가 목표치 (2.0%)",
            annotation_position="bottom right",
            annotation_font=dict(color="#facc15", size=11)
        )
        fig.add_hline(y=0.0, line_dash="solid", line_color="#475569", line_width=1, opacity=0.7)

    # 4. NBER 경기침체 음영 (Recession Shading)
    if show_recession and recession_periods:
        min_dt = df.index.min()
        max_dt = df.index.max()
        
        # 침체 구간별 대표 명칭 매핑 함수
        def get_recession_name(start_dt_str: str) -> str:
            yr = int(start_dt_str[:4])
            if yr in [1990, 1991]:
                return "걸프전·유가쇼크 침체 (1990)"
            elif yr == 2001:
                return "닷컴 버블 침체 (2001)"
            elif yr in [2007, 2008]:
                return "글로벌 금융위기 (2008)"
            elif yr == 2020:
                return "코로나19 침체 (2020)"
            else:
                return f"NBER 침체 ({yr})"

        for r_start, r_end in recession_periods:
            s_dt = pd.to_datetime(r_start)
            e_dt = pd.to_datetime(r_end)
            if e_dt < min_dt or s_dt > max_dt:
                continue
                
            eff_s = max(s_dt, min_dt).strftime("%Y-%m-%d")
            eff_e = min(e_dt, max_dt).strftime("%Y-%m-%d")
            recession_label = get_recession_name(r_start)
            
            # 고대비 밝은 실버/그레이 음영 + 양쪽 경계 점선으로 어두운 배경에서 확연히 구분되도록 적용
            fig.add_vrect(
                x0=eff_s,
                x1=eff_e,
                fillcolor="rgba(226, 232, 240, 0.16)", # 밝은 실버 반투명 음영
                layer="below",
                line_width=1,
                line_dash="dot",
                line_color="rgba(148, 163, 184, 0.45)", # 경계선 점선 표시
                annotation_text=recession_label,
                annotation_position="top left",
                annotation_font=dict(size=11, color="#e2e8f0")
            )

    # 5. 레이아웃 및 다크 Slate 테마 스타일링 (00 Bookmarks 무드)
    layout_dict = dict(
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        font=dict(color="#f8fafc", family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
        margin=dict(l=60, r=60, t=40, b=40),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1e293b",
            bordercolor="#475569",
            font=dict(color="#f8fafc", size=12)
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(30, 41, 59, 0.7)",
            bordercolor="#334155",
            borderwidth=1,
            font=dict(size=11, color="#f8fafc")
        ),
        xaxis=dict(
            gridcolor="#1e293b",
            zerolinecolor="#334155",
            tickfont=dict(color="#94a3b8", size=11),
            showspikes=True,
            spikemode="across",
            spikesnap="cursor",
            spikethickness=1,
            spikedash="dot",
            spikecolor="#64748b"
        ),
        yaxis=dict(
            title=dict(text=config.get("y1_label", ""), font=dict(color="#94a3b8", size=12)),
            gridcolor="#334155",
            zerolinecolor="#475569",
            tickfont=dict(color="#94a3b8", size=11),
            side="left"
        )
    )
    
    # 로그 스케일 처리
    if use_log_scale and config.get("supports_log_scale", False):
        if is_dual:
            # S&P 500이 있는 y2축을 로그 스케일로 적용
            fig.update_layout(yaxis2_type="log")
        else:
            layout_dict["yaxis"]["type"] = "log"
            
    fig.update_layout(**layout_dict)
    
    # 이중축 세부 레이아웃 적용
    if is_dual:
        fig.update_layout(
            yaxis2=dict(
                title=dict(text=config.get("y2_label", ""), font=dict(color="#4ade80", size=12)),
                tickfont=dict(color="#4ade80", size=11),
                side="right",
                overlaying="y",
                showgrid=False
            )
        )
        
    return fig
