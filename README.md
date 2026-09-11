# 주요 경제 지표 Review & Preview 대시보드

한국과 미국의 주요 거시 경제 지표를 한눈에 조회하고 비교 분석할 수 있는 인터랙티브 대시보드 애플리케이션입니다.

---

## 📌 주요 제공 지표 (11종)

1. **FED Target Rate & T10Y Yield & S&P 500**: 미국 연준 기준금리, 10년물 국채 금리 및 S&P 500 지수의 장기 상관관계 (이중축 지원)
2. **FED Target Rate & BOK Target Rate**: 미국 연준 기준금리와 한국은행 기준금리 및 한미 금리차(스프레드) 비교
3. **T10Y-T2Y Yield Spread & S&P 500**: 미국 10년-2년 국채 장단기 금리차 및 0% 역전 구간 하이라이트와 S&P 500 비교
4. **US Dollar Index**: 달러 인덱스 (DXY) 추이 및 이동평균선(50/200일)
5. **USD/KRW Exchange Rate**: 원/달러 환율 (1997~1998년 IMF 외환위기 환율 폭등 구간 완벽 복원)
6. **Crude Oil Prices: (WTI)**: 서부 텍사스산 원유(WTI) 가격 추이 ($/bbl)
7. **Producer Price Index (PPI) Total & Core**: 최종수요 생산자물가지수(PPI Final Demand) 및 근원(Core) 전년비(YoY %)
8. **Consumer Price Index (CPI) Total & Core**: 소비자물가지수 헤드라인 및 근원 인플레이션 전년비(YoY %)
9. **Personal Consumption Expenditures (PCE) Total & Core**: 연준 공식 물가안정 기준(2.0%) 헤드라인 및 근원 PCE 전년비(YoY %)
10. **Civilian Unemployment Rate**: 미국 민간 실업률 (%)
11. **Initial Jobless Claims**: 미국 주간 신규 실업수당 청구건수

---

## 🚀 주요 기능 및 특징

- **장기 시계열 완벽 분석**: 1990년 1월 1일부터 현재까지 약 36개년 시계열 지원
- **NBER 공식 경기침체 음영**:
  - 1990 걸프전·유가쇼크 침체
  - 2001 닷컴 버블 침체
  - 2008 글로벌 금융위기
  - 2020 코로나19 팬데믹
- **인터랙티브 툴팁(Tooltip)**: 마우스 커서 위치의 날짜와 모든 수치를 일목요연하게 표시
- **연준 2.0% 인플레이션 목표선**: 물가지수(PPI, CPI, PCE) 차트에 2% 타깃 기준선 자동 표시
- **원클릭 빠른 기간 선택**: `1Y`, `5Y`, `10Y`, `MAX` 및 캘린더 직접 입력 지원

---

## 🛠️ 로컬 실행 방법

1. 저장소 복제:
```bash
git clone https://github.com/sonosgg-debug/streamlit-15-MonthlyReview.git
cd streamlit-15-MonthlyReview
```

2. 필수 패키지 설치:
```bash
pip install -r requirements.txt
```

3. 대시보드 실행:
```bash
run_app.bat
# 또는
streamlit run app.py
```

---

## ☁️ Streamlit Community Cloud 배포 시 설정

Streamlit Cloud에 배포할 때는 대시보드의 **App settings > Secrets**에 API 키를 입력해 주세요:

```toml
FRED_API_KEY = "your_fred_api_key_here"
BOK_API_KEY = "your_bok_api_key_here"
```
