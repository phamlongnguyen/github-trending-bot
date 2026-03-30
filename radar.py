import requests
import os
import sys
import google.generativeai as genai
from datetime import datetime, timedelta

# ENV
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Cấu hình SDK Gemini
genai.configure(api_key=GEMINI_API_KEY)

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
        # Nếu lỗi HTML (do AI trả về ký tự lạ), gửi bản thô
        print(f"❌ Telegram HTML Error: {res.text}")
        requests.post(url, data={"chat_id": CHAT_ID, "text": "⚠️ Bản tin (Text-only):\n" + text[:1000]})

def run_radar(label="AUTO"):
    now = datetime.utcnow() + timedelta(hours=7)
    time_str = now.strftime("%d/%m/%Y %H:%M")
    
    print(f"🚀 [{label}] Đang quét GitHub AI...")
    
    # 1. Lấy Repo từ GitHub
    url = "https://api.github.com/search/repositories"
    # Lấy repo AI hot nhất mới cập nhật trong năm 2025/2026
    query = "stars:>20000 topic:ai pushed:>2025-01-01"
    
    try:
        res = requests.get(url, params={"q": query, "sort": "stars", "per_page": 6}, timeout=15).json()
        repos = res.get("items", [])
        
        if not repos:
            send_telegram(f"🕒 <code>{time_str}</code>\n<b>[{label}]</b> Không tìm thấy repo mới.")
            return

        repo_list = ""
        for r in repos:
            repo_list += f"- {r['full_name']} ({r['stargazers_count']} stars): {r['description']}\n"

        # 2. Gọi Gemini bằng SDK (Tránh lỗi 404 Endpoint)
        prompt = f"""
        Bạn là chuyên gia phân tích xu hướng công nghệ. Dựa trên các repo GitHub AI sau:
        {repo_list}
        
        Hãy viết bản tin Tiếng Việt theo ĐÚNG CẤU TRÚC sau (sử dụng emoji):
        
        ⚡ <b>AI Trend Hunter — Daily Brief</b>
        
        🔥 <b>TIÊU ĐIỂM</b>
        (Nhận định ngắn về xu hướng chung của các repo này)
        
        🚀 <b>TOP GITHUB TRENDING</b>
        (Liệt kê: • [Tên Repo] ⭐️ [Stars] — [Công dụng ngắn])
        
        💡 <b>INSIGHT NGẮN</b>
        (Nhận định cho Dev/Startup)
        
        📚 <b>Deep Dive — Full Tech Catalog</b>
        (Với mỗi repo, viết 1 câu về Startup Idea)
        
        LƯU Ý: KHÔNG dùng dấu gạch dưới (_) đơn lẻ, KHÔNG dùng markdown phức tạp. Chỉ dùng thẻ b và i của HTML.
        """

        # Sử dụng model flash qua SDK
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        if response.text:
            # Làm sạch text để tránh lỗi tag HTML của Telegram
            final_content = response.text.replace("**", "<b>").replace("__", "<i>")
            header = f"🕒 <code>{time_str}</code> | 🏷️ <code>{label}</code>\n\n"
            send_telegram(header + final_content)
            print("✅ Đã gửi bản tin thành công!")
        else:
            send_telegram("⚠️ AI trả về kết quả trống.")

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Lỗi: {error_msg}")
        send_telegram(f"❌ <b>Lỗi hệ thống:</b> <code>{error_msg}</code>")

if __name__ == "__main__":
    mode = "MANUAL" if len(sys.argv) > 1 and sys.argv[1] == "--manual" else "AUTO"
    run_radar(mode)
