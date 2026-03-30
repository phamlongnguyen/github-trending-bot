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

def analyze_repo(repo, model_name):
    prompt = f"""
    Phân tích chuyên sâu repo GitHub: {repo['full_name']}
    Mô tả: {repo['description']}
    Ngôn ngữ: {repo['language']}
    
    Trả về Tiếng Việt theo đúng 4 dòng sau:
    CONG_DUNG: (Giải thích thực tế nó dùng để làm gì)
    TAI_SAO_HOT: (Lý do đạt {repo['stargazers_count']} stars)
    STARTUP_IDEA: (Ý tưởng kinh doanh dựa trên công nghệ này)
    TOM_TAT: (Một câu ngắn gọn)
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
    try:
        res = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=25)
        data = res.json()
        if "candidates" in data:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return content.replace("<", "&lt;").replace(">", "&gt;")
        return "⚠️ AI không thể trích xuất dữ liệu."
    except Exception as e:
        return f"⚠️ Lỗi kết nối AI: {str(e)}"

def run_radar(label="AUTO"):
    # Lấy thời gian hiện tại (Định dạng: Thứ, Ngày/Tháng/Năm Giờ:Phút)
    # Lưu ý: GitHub Actions dùng giờ UTC, muốn giờ VN thì cộng thêm 7 tiếng
    now = datetime.utcnow() + timedelta(hours=7)
    time_str = now.strftime("%d/%m/%Y %H:%M")

    print(f"🚀 [{label}] [{time_str}] Đang quét GitHub AI...")
    model_name = get_model()
    
    url = "https://api.github.com/search/repositories"
    query = "stars:>20000 topic:ai pushed:>2024-01-01"
    
    try:
        res = requests.get(url, params={"q": query, "sort": "stars", "per_page": 10}, timeout=15).json()
        repos = res.get("items", [])
        
        if not repos:
            send_telegram(f"🕒 <code>{time_str}</code>\n<b>[{label}]</b> 😴 Không tìm thấy repo AI mới.")
            return

        for i, r in enumerate(repos, 1):
            analysis_raw = analyze_repo(r, model_name)
            
            lines = analysis_raw.split("\n")
            formatted_analysis = ""
            for line in lines:
                line = line.strip()
                if "CONG_DUNG:" in line: formatted_analysis += f"💡 <b>Công dụng:</b> {line.replace('CONG_DUNG:', '').strip()}\n"
                elif "TAI_SAO_HOT:" in line: formatted_analysis += f"🔥 <b>Tại sao hot:</b> {line.replace('TAI_SAO_HOT:', '').strip()}\n"
                elif "STARTUP_IDEA:" in line: formatted_analysis += f"🚀 <b>Startup Idea:</b> {line.replace('STARTUP_IDEA:', '').strip()}\n"
                elif "TOM_TAT:" in line: formatted_analysis += f"📝 <b>Tóm tắt:</b> {line.replace('TOM_TAT:', '').strip()}\n"

            if not formatted_analysis:
                formatted_analysis = analysis_raw

            # Message định dạng mới có Ngày/Giờ ở đầu
            msg = (
                f"🕒 <code>{time_str}</code> | #{i} 🏆\n"
                f"📂 <b>{r['name'].upper()}</b> [<code>{label}</code>]\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"⭐ Stars: <code>{r['stargazers_count']:,}</code>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{formatted_analysis}\n\n"
                f"🔗 <a href='{r['html_url']}'>XEM TRÊN GITHUB</a>"
            )
            
            send_telegram(msg)
            
    except Exception as e:
        send_telegram(f"❌ <b>Lỗi hệ thống:</b> <code>{str(e)}</code>")

if __name__ == "__main__":
    mode = "MANUAL" if len(sys.argv) > 1 and sys.argv[1] == "--manual" else "AUTO"
    run_radar(mode)
