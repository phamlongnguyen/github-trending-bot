import requests
import os
import sys
from openai import OpenAI
from datetime import datetime, timedelta

# ENV - Nhớ đổi GEMINI_API_KEY thành OPENAI_API_KEY trong GitHub Secrets
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Khởi tạo OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

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
        # Dự phòng nếu lỗi HTML tag
        requests.post(url, data={"chat_id": CHAT_ID, "text": "⚠️ Bản tin (Text-only):\n" + text[:1000]})

def run_radar(label="AUTO"):
    # Giờ VN (GMT+7)
    now = datetime.utcnow() + timedelta(hours=7)
    time_str = now.strftime("%d/%m/%Y %H:%M")
    
    print(f"🚀 [{label}] Quét GitHub AI và phân tích bằng OpenAI...")
    
    # 1. Lấy Repo từ GitHub
    url = "https://api.github.com/search/repositories"
    # Lấy repo AI hot nhất > 20k stars, cập nhật gần đây
    query = "stars:>20000 topic:ai pushed:>2025-01-01"
    
    try:
        res = requests.get(url, params={"q": query, "sort": "stars", "per_page": 6}, timeout=15).json()
        repos = res.get("items", [])
        
        if not repos:
            send_telegram(f"🕒 <code>{time_str}</code>\n<b>[{label}]</b> Không có repo mới đạt tiêu chuẩn.")
            return

        repo_list = ""
        for r in repos:
            repo_list += f"- {r['full_name']} ({r['stargazers_count']} stars): {r['description']}\n"

        # 2. Gọi OpenAI GPT-4o-mini (Nhanh, rẻ, thông minh)
        prompt = f"""
        Dựa trên danh sách các repo GitHub AI sau:
        {repo_list}
        
        Hãy viết bản tin Tiếng Việt theo ĐÚNG CẤU TRÚC HTML sau (sử dụng emoji):
        
        ⚡ <b>AI Trend Hunter — Daily Brief</b>
        
        🔥 <b>TIÊU ĐIỂM</b>
        (Nhận định ngắn về xu hướng chung của các repo này)
        
        🚀 <b>TOP GITHUB TRENDING</b>
        (Liệt kê: • [Tên Repo] ⭐️ [Stars] — [Công dụng ngắn])
        
        💡 <b>INSIGHT NGẮN</b>
        (Nhận định cho Dev/Startup)
        
        📚 <b>Deep Dive — Full Tech Catalog</b>
        (Với mỗi repo, viết 1 câu về Startup Idea dựa trên công năng thực tế của nó)
        
        LƯU Ý: 
        - Trả về text đã bao bọc trong thẻ <b> và <i> của HTML. 
        - Không dùng Markdown (**), không dùng ký tự lạ.
        - Phân tách các phần rõ ràng.
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini", # Model cực kỳ ổn định
            messages=[{"role": "system", "content": "Bạn là chuyên gia phân tích công nghệ AI."},
                      {"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        analysis = response.choices[0].message.content
        
        # Header thời gian
        header = f"🕒 <code>{time_str}</code> | 🏷️ <code>{label}</code>\n\n"
        send_telegram(header + analysis)
        print("✅ OpenAI đã phân tích và gửi tin thành công!")

    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
        send_telegram(f"❌ <b>Lỗi hệ thống:</b> <code>{str(e)}</code>")

if __name__ == "__main__":
    mode = "MANUAL" if len(sys.argv) > 1 and sys.argv[1] == "--manual" else "AUTO"
    run_radar(mode)
