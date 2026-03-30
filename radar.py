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
    print(f"🚀 [{label}] Đang quét GitHub AI (>20k Stars)...")
    model_name = get_model()
    
    url = "https://api.github.com/search/repositories"
    # QUERY: Lọc cực mạnh > 20.000 stars, liên quan đến AI/Claude và mới cập nhật
    last_month = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    query = f"stars:>20000 pushed:>{last_month} topic:ai"
    
    try:
        # Lấy 10 repo khủng nhất
        res = requests.get(url, params={"q": query, "sort": "stars", "per_page": 10}, timeout=15).json()
        repos = res.get("items", [])
        
        if not repos:
            send_telegram(f"<b>[{label}]</b> 😴 Không tìm thấy repo AI nào > 20k stars mới cập nhật.")
            return

        for i, r in enumerate(repos, 1):
            # Prompt yêu cầu phân tích sâu hơn
            prompt = f"""
            Hãy phân tích repo GitHub này: {r['full_name']}
            Mô tả gốc: {r['description']}
            
            Yêu cầu trả về bằng Tiếng Việt, định dạng HTML:
            1. 'Công dụng thực tế': Repo này dùng để làm gì trong thực tế? (Phân tích sâu)
            2. 'Tại sao hot': Tại sao nó đạt hơn 20k stars?
            3. 'Startup Idea': Một ý tưởng kinh doanh từ repo này.
            4. 'Tóm tắt 1 câu': Ngắn gọn nhất có thể.
            """
            
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
            ai_res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
            
            if "candidates" in ai_res:
                analysis = ai_res["candidates"][0]["content"]["parts"][0]["text"]
                # Xử lý bảo mật HTML cơ bản
                analysis = analysis.replace("<br>", "\n").replace("<b>", "<b>").replace("</b>", "</b>")
            else:
                analysis = "<i>(AI gặp lỗi khi phân tích sâu repo này)</i>"

            # Định dạng tin nhắn gửi đi
            msg = (
                f"🏆 <b>TOP AI REPO #{i}</b> 🏷️ <code>{label}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🔥 <b>Tên:</b> {r['name'].upper()}\n"
                f"⭐ <b>Stars:</b> <code>{r['stargazers_count']:,}</code>\n"
                f"🌐 <b>Ngôn ngữ:</b> {r['language'] or 'N/A'}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{analysis}\n\n"
                f"🔗 <a href='{r['html_url']}'>TRUY CẬP GITHUB</a>\n"
                f"━━━━━━━━━━━━━━━━━━━━"
            )
            
            send_telegram(msg)
            
    except Exception as e:
        send_telegram(f"❌ <b>Lỗi hệ thống:</b> <code>{str(e)}</code>")

if __name__ == "__main__":
    mode = "MANUAL" if len(sys.argv) > 1 and sys.argv[1] == "--manual" else "AUTO"
    run_radar(mode)
