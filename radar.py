import requests
import os
from datetime import datetime, timedelta

# ENV - Thiết lập trên GitHub Secrets hoặc file .env
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------------- FETCH (Quét Công nghệ AI) ----------------
def get_ai_repos():
    url = "https://api.github.com/search/repositories"
    
    # Lấy các repo có cập nhật (pushed) trong 7 ngày qua
    last_week = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # Query: Tìm theo topic AI, stars trên 500 để đảm bảo chất lượng
    query = f"topic:ai topic:machine-learning stars:>500 pushed:>{last_week}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 5  # Lấy 5 con hot nhất mỗi lần chạy
    }

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else "",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        data = res.json()
        if "items" not in data:
            print(f"❌ GitHub API Error: {data.get('message')}")
            return []
        return data.get("items", [])
    except Exception as e:
        print(f"❌ GitHub Request Failed: {e}")
        return []

# ---------------- AI (Phân tích bằng Gemini v1) ----------------
def analyze_with_gemini(repo):
    prompt = f"""
Bạn là một chuyên gia AI cao cấp. Hãy tóm tắt Repo sau bằng Tiếng Việt:
Tên: {repo['full_name']}
Stars: {repo['stargazers_count']}
Mô tả: {repo['description']}

Yêu cầu (ngắn gọn, xuống dòng hợp lý):
- 💡 Công dụng: 
- 🔥 Điểm nổi bật công nghệ:
- 🚀 Ý tưởng Startup:
- ⚡ Đánh giá nhanh:
"""

    # Sử dụng phiên bản v1 ổn định để tránh lỗi 404
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        res = requests.post(url, json=payload, timeout=20)
        data = res.json()
        
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"❌ Gemini API Error: {data}")
            return "⚠️ AI không phản hồi nội dung."
    except Exception as e:
        print(f"❌ Gemini Request Failed: {e}")
        return "⚠️ Lỗi kết nối AI."

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🤖 AI GitHub Radar is starting (No-Duplicate-Logic Disabled)...")

    if not GEMINI_API_KEY:
        print("❌ Lỗi: Thiếu GEMINI_API_KEY!")
        exit()

    # Lấy danh sách repo
    repos = get_ai_repos()

    if not repos:
        print("😴 Không có repo AI nào mới đạt tiêu chuẩn hôm nay.")
        exit()

    print(f" tìm thấy {len(repos)} repo hot. Đang phân tích...")

    for r in repos:
        analysis = analyze_with_gemini(r)
        
        # Xây dựng tin nhắn Telegram
        msg = (
            f"🌟 *AI TRENDING RADAR* 🌟\n\n"
            f"📦 *{r['full_name']}* ({r['stargazers_count']}⭐)\n"
            f"{analysis}\n"
            f"🔗 [Link GitHub]({r['html_url']})"
        )

        # Gửi tới Telegram
        try:
            tel_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(tel_url, data={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
                "disable_web_page_preview": False
            }, timeout=10)
            print(f"✅ Đã gửi: {r['full_name']}")
        except Exception as e:
            print(f"❌ Telegram error: {e}")

    print("🏁 Xong! Kiểm tra điện thoại của bạn.")
