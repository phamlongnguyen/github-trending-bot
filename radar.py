import requests
import os
import json
from datetime import datetime, timedelta

# ENV
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
# Đổi tên biến môi trường cho đúng mục đích
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

STATE_FILE = "sent.json"

# ---------------- STATE ----------------
def load_sent():
    try:
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_sent(data):
    with open(STATE_FILE, "w") as f:
        json.dump(list(data), f)

# ---------------- FETCH ----------------
def get_repos():
    url = "https://api.github.com/search/repositories"
    last_week = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Query: Star > 30k và có push trong tuần qua
    query = f"stars:>30000 pushed:>{last_week}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 10
    }

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else ""
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        data = res.json()
        return data.get("items", [])
    except Exception as e:
        print("❌ GitHub API error:", e)
        return []

# ---------------- AI (GEMINI REPLACEMENT) ----------------
def analyze(repo):
    prompt = f"""
Bạn là một chuyên gia phân tích Startup. Hãy phân tích Repo sau:
Repo: {repo['full_name']}
Stars: {repo['stargazers_count']}
Mô tả: {repo['description']}

Yêu cầu trả về ngắn gọn:
- Nó làm gì?
- Tại sao nó trending?
- Ý tưởng Startup từ repo này?
- Đánh giá nhanh (Verdict).
"""

    # URL API của Gemini (Dùng model flash cho nhanh và miễn phí)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=15)
        data = res.json()

        # Kiểm tra lỗi từ Google API
        if "candidates" not in data:
            print("DEBUG Gemini Error:", data)
            return "⚠️ Gemini AI error"

        return data["candidates"][0]["content"]["parts"][0]["text"]

    except Exception as e:
        print(f"❌ Gemini request failed for {repo['full_name']}:", e)
        return "⚠️ AI request failed"

# ---------------- BUILD MSG ----------------
def build_msg(repos):
    msg = "🚀 *30K+ GitHub Radar (Powered by Gemini)*\n\n"

    for r in repos:
        ai_analysis = analyze(r)
        
        msg += f"🔥 *{r['full_name']}* ({r['stargazers_count']}⭐)\n"
        msg += f"{ai_analysis}\n"
        msg += f"🔗 {r['html_url']}\n"
        msg += "---------------------------\n\n"

    return msg

# ---------------- TELEGRAM ----------------
def send_telegram(text):
    if not text.strip():
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Chia nhỏ tin nhắn nếu quá dài (Telegram giới hạn 4096 ký tự)
    try:
        res = requests.post(url, data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
        print("Telegram status:", res.status_code)
    except Exception as e:
        print("❌ Telegram error:", e)

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🚀 Radar bot starting with Gemini...")

    if not GEMINI_API_KEY:
        print("❌ Lỗi: Thiếu GEMINI_API_KEY trong môi trường!")
        exit()

    sent = load_sent()
    repos = get_repos()

    if not repos:
        print("😴 No repos found.")
        exit()

    # Lọc repo mới
    new_repos = [r for r in repos if r["full_name"] not in sent]

    if not new_repos:
        print("😴 No new repos today.")
        exit()

    # Xử lý từng cụm (nên giới hạn để tránh spam Telegram)
    final_msg = build_msg(new_repos[:3]) # Lấy 3 cái mới nhất để tránh quá dài
    send_telegram(final_msg)

    # Lưu lại những cái đã gửi
    for r in new_repos:
        sent.add(r["full_name"])
    save_sent(sent)

    print("✅ Done!")
