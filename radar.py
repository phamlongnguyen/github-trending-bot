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
    now = datetime.utcnow() + timedelta(hours=7)
    time_str = now.strftime("%d/%m/%Y %H:%M")

    print(f"🚀 [{label}] Đang quét GitHub AI...")
    model_name = get_model()
    
    url = "https://api.github.com/search/repositories"
    # Lấy 5 repo AI khủng nhất để tóm tắt thành 1 bản tin Daily Brief
    query = "stars:>20000 topic:ai pushed:>2024-01-01"
    
    try:
        res = requests.get(url, params={"q": query, "sort": "stars", "per_page": 5}, timeout=15).json()
        repos = res.get("items", [])
        
        if not repos:
            send_telegram(f"🕒 <code>{time_str}</code>\n<b>[{label}]</b> Không thấy repo mới.")
            return

        # CHUẨN BỊ DỮ LIỆU GỬI AI TỔNG HỢP
        repo_data_for_ai = ""
        for r in repos:
            repo_data_for_ai += f"- {r['full_name']} ({r['stargazers_count']} stars): {r['description']}\n"

        prompt = f"""
        Dựa trên danh sách các repo GitHub AI sau:
        {repo_data_for_ai}
        
        Hãy viết một bản tin chuyên sâu theo đúng format sau (Tiếng Việt):
        
        ⚡ **AI Trend Hunter — Daily Brief**
        
        🔥 **TIÊU ĐIỂM**
        (Viết 1 đoạn ngắn về xu hướng chung của các repo này, ví dụ: AI Agent, LLM hay Vibe Coding)
        
        🚀 **TOP GITHUB TRENDING**
        (Liệt kê các repo theo format: • [Tên Repo] ⭐️ [Stars] — [Tóm tắt công dụng ngắn gọn])
        
        💡 **INSIGHT NGẮN**
        (1 câu nhận định về giá trị cho Senior Dev hoặc Startup)
        
        📚 **Deep Dive — Full Tech Catalog**
        (Phân tích chi tiết hơn 1-2 dòng cho mỗi repo về công nghệ sử dụng và Startup idea)
        """

        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        ai_res = requests.post(api_url, json={"contents": [{"parts": [{"text": prompt}]}]}).json()
        
        if "candidates" in ai_res:
            final_content = ai_res["candidates"][0]["content"]["parts"][0]["text"]
            # Format lại các thẻ HTML cho chuẩn Telegram
            final_content = final_content.replace("**", "<b>").replace("**", "</b>") # Nếu AI trả về Markdown
            
            # GỬI TIN NHẮN TỔNG HỢP
            header = f"🕒 <code>{time_str}</code> | 🏷️ <code>{label}</code>\n\n"
            send_telegram(header + final_content)
            print("✅ Đã gửi bản tin Daily Brief thành công!")
        else:
            send_telegram("⚠️ AI không thể tổng hợp bản tin hôm nay.")

    except Exception as e:
        send_telegram(f"❌ Lỗi: {str(e)}")

if __name__ == "__main__":
    mode = "MANUAL" if len(sys.argv) > 1 and sys.argv[1] == "--manual" else "AUTO"
    run_radar(mode)
