import requests
import os
import sys
import re
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

def clean_html(text):
    """Chuyển đổi Markdown từ AI sang HTML chuẩn Telegram"""
    # Chuyển **text** thành <b>text</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Chuyển * text thành • text
    text = re.sub(r'^\* ', r'• ', text, flags=re.MULTILINE)
    # Loại bỏ các ký tự < > lạ để tránh lỗi tag HTML
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    # Trả lại các tag b và i chuẩn
    text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    text = text.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</b>")
    return text

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
        # Nếu lỗi HTML, gửi bản text thuần làm dự phòng
        clean_text = re.sub('<[^<]+?>', '', text)
        requests.post(url, data={"chat_id": CHAT_ID, "text": "⚠️ Lỗi định dạng, gửi bản thô:\n" + clean_text})

def run_radar(label="AUTO"):
    now = datetime.utcnow() + timedelta(hours=7)
    time_str = now.strftime("%d/%m/%Y %H:%M")

    print(f"🚀 [{label}] Đang quét GitHub AI...")
    model_name = get_model()
    
    # Lấy 5-7 repo AI hot nhất > 20k stars
    url = "https://api.github.com/search/repositories"
    query = "stars:>20000 topic:ai pushed:>2025-01-01"
    
    try:
        res = requests.get(url, params={"q": query, "sort": "stars", "per_page": 7}, timeout=15).json()
        repos = res.get("items", [])
        
        if not repos:
            send_telegram(f"🕒 <code>{time_str}</code>\n<b>[{label}]</b> 😴 Không thấy repo mới.")
            return

        repo_list = ""
        for r in repos:
            repo_list += f"- {r['full_name']} ({r['stargazers_count']} stars): {r['description']}\n"

        prompt = f"""
        Bạn là chuyên gia phân tích xu hướng công nghệ. Dựa trên các repo GitHub AI sau:
        {repo_list}
        
        Hãy viết bản tin Tiếng Việt theo ĐÚNG CẤU TRÚC sau (sử dụng emoji như ảnh mẫu):
        
        ⚡ **AI Trend Hunter — Daily Brief**
        
        🔥 **TIÊU ĐIỂM**
        (Viết 1 đoạn nhận định về xu hướng chung của các repo này)
        
        🚀 **TOP GITHUB TRENDING**
        (Liệt kê dạng danh sách: • [Tên Repo] ⭐️ [Stars] — [Công dụng ngắn gọn])
        
        💡 **INSIGHT NGẮN**
        (Nhận định giá trị cho Developer/Startup)
        
        📚 **Deep Dive — Full Tech Catalog**
        (Với mỗi repo, viết 1-2 câu về Startup Idea và cách áp dụng thực tế)
        """

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        ai_res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=30).json()
        
        if "candidates" in ai_res:
            raw_text = ai_res["candidates"][0]["content"]["parts"][0]["text"]
            formatted_content = clean_html(raw_text)
            
            final_msg = f"🕒 <code>{time_str}</code> | 🏷️ <code>{label}</code>\n\n{formatted_content}"
            send_telegram(final_msg)
            print("✅ Đã gửi bản tin Daily Brief thành công!")
        else:
            print(f"❌ Gemini Response Error: {ai_res}")
            send_telegram(f"⚠️ AI lỗi: {ai_res.get('error', {}).get('message', 'Unknown error')}")

    except Exception as e:
        send_telegram(f"❌ Lỗi hệ thống: {str(e)}")

if __name__ == "__main__":
    mode = "MANUAL" if len(sys.argv) > 1 and sys.argv[1] == "--manual" else "AUTO"
    run_radar(mode)
