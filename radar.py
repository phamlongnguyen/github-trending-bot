import requests
import os
from datetime import datetime, timedelta

# ENV
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ---------------- LẤY MODEL KHẢ DỤNG ----------------
def get_available_model():
    """Tự động tìm model mà API Key của bạn có quyền sử dụng"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json()
        if "models" in data:
            # Ưu tiên tìm các model flash hoặc pro có hỗ trợ generateContent
            for m in data["models"]:
                name = m["name"].split("/")[-1]
                if "generateContent" in m["supportedGenerationMethods"]:
                    if "flash" in name or "pro" in name:
                        print(f"✅ Đã tự động chọn model: {name}")
                        return name
            return data["models"][0]["name"].split("/")[-1]
    except Exception as e:
        print(f"❌ Không thể liệt kê model: {e}")
    return "gemini-1.5-flash" # Fallback mặc định

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
    except: return []

# ---------------- AI ANALYSIS ----------------
def analyze_with_gemini(repo, model_name):
    prompt = f"Tóm tắt repo AI này bằng Tiếng Việt: {repo['full_name']}. Mô tả: {repo['description']}. Yêu cầu: Công dụng, Điểm nổi bật, Startup idea."
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        res = requests.post(url, json=payload, timeout=20)
        data = res.json()
        if "candidates" in data:
            return data["candidates"][0]["content"]["parts"][0]["text"], None
        return None, data.get("error", {}).get("message", str(data))
    except Exception as e:
        return None, str(e)

# ---------------- TELEGRAM ----------------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"})

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("🤖 AI GitHub Radar is starting...")
    
    # BƯỚC 1: Tự động tìm model đúng cho Key của bạn
    active_model = get_available_model()
    
    repos = get_ai_repos()
    if not repos:
        send_telegram("❌ GitHub không trả về dữ liệu.")
        exit()

    errors = []
    for r in repos:
        analysis, err = analyze_with_gemini(r, active_model)
        if err:
            errors.append(f"Repo *{r['full_name']}*: {err}")
            continue

        msg = f"🌟 *AI TRENDING RADAR*\n📦 *{r['full_name']}*\n\n{analysis}\n\n🔗 [Link]({r['html_url']})"
        send_telegram(msg)

    if errors:
        send_telegram("⚠️ *BÁO CÁO LỖI AI*\n" + "\n".join(errors[:2]))
    print("🏁 Xong!")
