import os
import time
import requests
import html
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from google import genai

# ==========================================
# 0. Render 무료 Web Service 포트 바인딩 속임수
# ==========================================
def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), BaseHTTPRequestHandler)
    server.serve_forever()

# 스레드로 가짜 웹서버 포트 실행
threading.Thread(target=run_dummy_server, daemon=True).start()

# ==========================================
# 1. 환경변수 및 클라이언트 로드
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

client = genai.Client(api_key=GEMINI_API_KEY)

# ==========================================
# 2. 텔레그램 메시지 송수신 함수
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
# 3. AI 멀티 에이전트 토론 엔진 (2회 회전)
# ==========================================
def run_debate(stock_name):
    news_data = get_naver_news(stock_name)
    
    prompt = f"""
당신은 최고의 주식 분석 AI 시스템입니다. 입력된 종목 [{stock_name}]에 대해 아래 3개 에이전트가 2회 교차 토론을 거쳐 최종 투자 판단을 내리는 리포트를 작성하세요.

[수집된 종목 최신 뉴스/재료]
{news_data}

---
[토론 진행 및 리포트 작성 가이드]

1. **📊 Agent 1: 재무/가치평가 분석가**
   - 기업의 펀더멘털, 밸류에이션(PER/PBR 추정), 적정주가 범위 및 재무적 안정성/리스크 진단.

2. **📰 Agent 2: 뉴스/모멘텀 분석가**
   - 최근 이슈, 수주, 업황, 테마 모멘텀 및 수집된 뉴스의 감성(호재 vs 악재) 분석.

3. **📈 Agent 3: 차트/수급 분석가**
   - 수급 흐름(외인/기관 동향 추정), 과매도/과매수 여부, 지지/저항선 기반의 매수/매도 타이밍 평가.

4. **⚔️ Agent 간 2회 회전 토론 요약 (Debate Rounds)**
   - Round 1: 각 에이전트의 초기 의견 충돌 및 상호 반박
   - Round 2: 반박에 대한 재반박 및 리스크 요인 교차 검증

5. **⚖️ Moderator(사회자) 최종 판정**
   - **투자의견**: [매수 / 관망 / 매도]
   - **목표 접근 전략**: (예: 분할 매수 / 지지선 확인 후 접근 등)
   - **투자 리포트 요약점수**: [★ 1~5점]
   - **핵심 이유**: 2줄 요약

모바일 텔레그램에서 읽기 쉽게 이모지와 불렛 포인트를 활용하여 명확히 작성해 주세요.
"""
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"토론 중 오류가 발생했습니다: {e}"

# ==========================================
# 4. 24시간 텔레그램 폴링 루프 (Render 대기형)
# ==========================================
def main():
    print("🤖 Stock Debate Bot 시작 (24시간 대기 중)...")
    last_update_id = 0
    
    # 봇 시작 안내
    send_telegram("🤖 [AI 주식 토론 봇 알림]\n서버가 가동되었습니다. 텔레그램에 '/토론 종목명' (예: /토론 HL디앤아이한라)을 입력하시면 3개 에이전트 토론을 시작합니다.")

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
                        send_telegram(f"🔍 [{stock_name}] 종목을 대상으로 3개 에이전트(재무·뉴스·차트)가 2회 회전 토론을 시작합니다. 약 15~30초 소요됩니다...")
                        
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
