import requests
import os
from datetime import datetime, timedelta

# ENV
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------------- FETCH AI REPOS ----------------
def get_ai_repos():
    url = "https://api.github.com/search/repositories"
    last_week = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    query = f"topic:ai topic:machine-learning stars:>500 pushed:>{last_week}"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": 5}
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}" if GITHUB_TOKEN else ""}
    try:
        res = requests.get(url, headers=headers, params=params, timeout=15)
        return res.json().get("items", [])
    except:
        return []

# ---------------- AI ANALYSIS (VỚI CƠ CHẾ DỰ PHÒNG) ----------------
def analyze_with_gemini(repo):
    prompt = f"Tóm tắt ngắn gọn repo AI này bằng Tiếng Việt: {repo['full_name']}. Mô tả: {repo['description']}. Yêu cầu: Công dụng, Điểm nổi bật, Ý tưởng Startup."

    # Thử lần lượt các tên model phổ biến nhất
    models_to_try = ["gemini-1.5-flash-latest", "gemini-1.5-flash", "gemini-pro"]
    
    last_error = ""
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        try:
            res = requests.post(url, json=payload, timeout=20)
            data = res.json()
            
            if "candidates" in data:
                return data["candidates"][0]["content"]["parts"][0]["text"], None
            else:
                last_error = data.get("error", {}).get("message", "Unknown error")
                print(f"⚠️ Thử model {model_name} thất bại: {last_error}")
        except Exception as e:
            last_error = str(e)
            
    return None, last_error

# ---------------- TELEGRAM ----------------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Dùng Markdown để định dạng đẹp hơn
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🤖 AI GitHub Radar is starting...")
    
    repos = get_ai_repos()
    if not repos:
        send_telegram("❌ GitHub API không trả về dữ liệu.")
        exit()

    errors = []
    success_count = 0

    for r in repos:
        analysis, err = analyze_with_gemini(r)
        
        if err:
            errors.append(f"Repo *{r['full_name']}*: {err}")
            continue

        msg = (
            f"🌟 *AI TRENDING RADAR* 🌟\n\n"
            f"📦 *{r['full_name']}* ({r['stargazers_count']}⭐)\n\n"
            f"{analysis}\n\n"
            f"🔗 [Link GitHub]({r['html_url']})"
        )
        send_telegram(msg)
        success_count += 1

    # Báo cáo lỗi nếu có
    if errors:
        error_report = "⚠️ *BÁO CÁO LỖI AI*\n\n" + "\n".join(errors[:3]) # Gửi tối đa 3 lỗi để tránh spam
        send_telegram(error_report)

    print(f"✅ Xong! Thành công: {success_count}, Thất bại: {len(errors)}")
