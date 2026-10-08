import os
import time
import requests
import html
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from google import genai

# ==========================================
# 0. Render 무료 Web Service 포트 바인딩 우회 스레드
# ==========================================
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), BaseHTTPRequestHandler)
    server.serve_forever()

# 백그라운드 스레드로 가짜 포트 개설
threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# 1. 환경변수 및 API 클라이언트 설정
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. 텔레그램 및 네이버 뉴스 유틸리티 함수
# ==========================================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def clean_html(text):
    text = html.unescape(text)
    return re.sub(r'<[^>]+>', '', text)

def get_naver_news(stock_name):
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    url = f"https://openapi.naver.com/v1/search/news.json?query={stock_name}&display=5&sort=date"
    try:
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            items = res.json().get('items', [])
            news_txt = ""
            for item in items:
                title = clean_html(item['title'])
                desc = clean_html(item['description'])
                news_txt += f"- {title}: {desc}\n"
            return news_txt
    except Exception as e:
        print(f"뉴스 수집 실패: {e}")
    return "뉴스 수집 데이터 없음"

# ==========================================
# 3. 상세 토론 반영 AI 멀티 에이전트 토론 엔진
# ==========================================
def run_debate(stock_name):
    news_data = get_naver_news(stock_name)
    
    prompt = f"""
당신은 최고의 주식 분석 AI 시스템입니다. 입력된 종목 [{stock_name}]에 대해 아래 3개 분야 전문 에이전트의 상세한 주장과 상호 교차 토론, 최종 판단이 포함된 리포트를 작성하세요.

[최신 뉴스 데이터]
{news_data}

---
[작성 가이드 및 양식]

📊 **1. 재무/가치평가 에이전트**
- 펀더멘털, 밸류에이션(PER/PBR), 재무적 리스크 및 적정 주가 수준 분석

📰 **2. 뉴스/모멘텀 에이전트**
- 최신 이슈, 호재/악재 감성 분석, 산업 모멘텀 및 핵심 재료 평가

📈 **3. 차트/수급 에이전트**
- 외국인/기관 수급 동향, 과매도·과매수 지표, 지지/저항선 및 기술적 매매 타이밍

⚔️ **에이전트 교차 토론 (Debate)**
- **주요 쟁점**: 각 에이전트 간 시각 차이 및 상호 반박 내용 (2~3줄)
- **리스크 검증**: 투자 시 반드시 주의해야 할 핵심 우려 사항 (1~2줄)

⚖️ **사회자(Moderator) 최종 판정**
- **투자의견**: [매수 / 관망 / 매도]
- **목표 접근 전략**: (예: 분할 매수 전략, 지지선 확인 후 접근 등 구체적 가이드)
- **요약점수**: [★ 1~5점]
- **핵심 투자 포인트**: 2줄 요약

* 각 에이전트의 주장을 명확한 문장과 불렛 포인트, 이모지를 활용해 읽기 쉽게 작성해 주세요.
"""
    
    # 503 에러 방지를 위한 백업 모델 순차 호출 목록
    target_models = ['gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-1.5-flash']
    
    for model_id in target_models:
        for attempt in range(2):  # 모델당 최대 2회 재시도
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                print(f"[{model_id}] 호출 실패 (시도 {attempt+1}): {e}")
                time.sleep(1.5)
                
    return "현재 구글 API 서버 트래픽이 일시적으로 과도하여 응답을 완료하지 못했습니다. 잠시 후 다시 시도해 주세요."

# ==========================================
# 4. 24시간 텔레그램 폴링 루프
# ==========================================
def main():
    print("🤖 Stock Debate Bot 시작 (24시간 대기 중)...")
    last_update_id = 0
    
    # 봇 가동 완료 알림
    send_telegram("🤖 [AI 주식 토론 봇 알림]\n서버가 상세 토론 버전으로 가동되었습니다.\n텔레그램에 '/토론 종목명' (예: /토론 HL디앤아이한라)을 입력하시면 분석 리포트를 전달합니다.")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            res = requests.get(url).json()
            
            for result in res.get("result", []):
                last_update_id = result["update_id"]
                message = result.get("message", {})
                text = message.get("text", "")
                
                if text.startswith("/토론"):
                    parts = text.split()
                    if len(parts) >= 2:
                        stock_name = parts[1]
                        send_telegram(f"🔍 [{stock_name}] 3개 에이전트 토론 및 리포트를 작성 중입니다. 약 10~15초 소요됩니다...")
                        
                        # 토론 실행
                        report = run_debate(stock_name)
                        send_telegram(report)
                    else:
                        send_telegram("⚠️ 올바른 형식으로 입력해 주세요.\n예: `/토론 삼성전자` 또는 `/토론 HL디앤아이한라`")
                        
        except Exception as e:
            print(f"폴링 중 오류 발생: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
