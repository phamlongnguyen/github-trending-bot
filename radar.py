import requests
import os
import sys
from datetime import datetime, timedelta

# ENV
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def get_model():
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        for m in res.get("models", []):
            name = m["name"].split("/")[-1]
            if "generateContent" in m["supportedGenerationMethods"] and "1.5-flash" in name:
                return name
    except: pass
    return "gemini-1.5-flash"

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    res = requests.post(url, data=payload, timeout=10)
    if not res.json().get("ok"):
        print(f"❌ Telegram Error: {res.text}")

def run_radar(label="AUTO"):
    print(f"🚀 [{label}] Đang quét GitHub AI & Claude...")
    model_name = get_model()
    
    url = "https://api.github.com/search/repositories"
    # Lấy repo liên quan đến Claude, AI và có hoạt động gần đây
    # Query: 'claude' kết hợp với các topic AI
    query = "claude AI topic:ai topic:machine-learning stars:>100"
    
    try:
        # per_page=10 để lấy đúng 10 repo
        res = requests.get(url, params={"q": query, "sort": "stars", "per_page": 10}, timeout=15).json()
        repos = res.get("items", [])
        
        if not repos:
            send_telegram(f"<b>[{label}]</b> 😴 Không tìm thấy repo Claude/AI nào mới.")
            return

        for i, r in enumerate(repos, 1):
            prompt = f"Tóm tắt repo GitHub: {r['full_name']}. Mô tả: {r['description']}. Viết ngắn gọn 3 dòng: Công dụng, Điểm nổi bật, Cách dùng. Tiếng Việt."
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            
            ai_res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
            
            if "candidates" in ai_res:
                analysis = ai_res["candidates"][0]["content"]["parts"][0]["text"]
                analysis = analysis.replace("<", "&lt;").replace(">", "&gt;").strip()
            else:
                analysis = "<i>(AI không thể phân tích nội dung này)</i>"

            # ĐỊNH DẠNG TIN NHẮN MỚI: Phân biệt rõ Title, Label và Body
            msg = (
                f"#{i} | <b>{r['name'].upper()}</b> 🏷️ <code>{label}</code>\n"
                f"───────────────────\n"
                f"⭐ <b>Stars:</b> {r['stargazers_count']}\n"
                f"📝 <b>Mô tả:</b> <i>{r['description']}</i>\n\n"
                f"🤖 <b>AI Phân tích:</b>\n{analysis}\n\n"
                f"🔗 <a href='{r['html_url']}'>Xem dự án trên GitHub</a>\n"
                f"───────────────────"
            )
            
            send_telegram(msg)
            
    except Exception as e:
        send_telegram(f"❌ <b>Lỗi hệ thống:</b> <code>{str(e)}</code>")

if __name__ == "__main__":
    mode = "MANUAL" if len(sys.argv) > 1 and sys.argv[1] == "--manual" else "AUTO"
    run_radar(mode)
