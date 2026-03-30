import requests
import os
import json
from datetime import datetime, timedelta

# ENV
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

STATE_FILE = "sent.json"


# ---------------- STATE ----------------
def load_sent():
    try:
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()


def save_sent(data):
    with open(STATE_FILE, "w") as f:
        json.dump(list(data), f)


# ---------------- FETCH ----------------
def get_repos():
    url = "https://api.github.com/search/repositories"

    last_week = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    query = f"stars:>30000 pushed:>{last_week}"

    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 20
    }

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}"
    }

    res = requests.get(url, headers=headers, params=params, timeout=10)
    data = res.json()

    repos = []
    for item in data.get("items", []):
        repos.append({
            "name": item["full_name"],
            "desc": item["description"] or "",
            "stars": item["stargazers_count"],
            "url": item["html_url"]
        })

    return repos


# ---------------- AI ----------------
def analyze(repo):
    prompt = f"""
You are a startup analyst.

Repo: {repo['name']}
Stars: {repo['stars']}
Description: {repo['desc']}

Return:
- What it does
- Why it's trending
- Startup angle (realistic)
- Verdict (short)
"""

    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        },
        timeout=15
    )

    return res.json()["choices"][0]["message"]["content"]


# ---------------- BUILD MSG ----------------
def build_msg(repos):
    msg = "🚀 *30K+ GitHub Radar (10 repos/day)*\n\n"

    for r in repos:
        ai = analyze(r)

        msg += f"🔥 *{r['name']}* ({r['stars']}⭐)\n"
        msg += f"{ai}\n"
        msg += f"{r['url']}\n\n"

    return msg


# ---------------- TELEGRAM ----------------
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }, timeout=10)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    sent = load_sent()

    repos = get_repos()

    # lọc repo mới
    new_repos = [r for r in repos if r["name"] not in sent]

    # sort theo stars
    new_repos = sorted(new_repos, key=lambda x: x["stars"], reverse=True)

    # lấy tối đa 10 repo
    new_repos = new_repos[:10]

    if not new_repos:
        send_telegram("😴 No new repos today")
    else:
        msg = build_msg(new_repos)
        send_telegram(msg)

        # update state
        for r in new_repos:
            sent.add(r["name"])

        save_sent(sent)
