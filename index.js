import axios from "axios";
import TelegramBot from "node-telegram-bot-api";
import dotenv from "dotenv";
import Groq from "groq-sdk";
import { readFileSync, writeFileSync } from "fs";

dotenv.config();

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN);
const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

const GITHUB_HEADERS = {
  Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
  Accept: "application/vnd.github.v3+json",
};

const SENT_FILE = "./sent.json";

// ─── Dedup helpers ────────────────────────────────────────────────────────────

function loadSent() {
  try {
    return new Set(JSON.parse(readFileSync(SENT_FILE, "utf-8")));
  } catch {
    return new Set();
  }
}

function saveSent(sentSet) {
  const list = [...sentSet].slice(-200); // giữ tối đa 200 repo gần nhất
  writeFileSync(SENT_FILE, JSON.stringify(list));
}

// ─── GitHub fetchers ──────────────────────────────────────────────────────────

async function fetchRepos(query, perPage = 4) {
  try {
    const res = await axios.get("https://api.github.com/search/repositories", {
      params: { q: query, sort: "stars", order: "desc", per_page: perPage },
      headers: GITHUB_HEADERS,
    });
    return res.data.items || [];
  } catch (err) {
    console.error(`GitHub Error [${query}]:`, err.message);
    return [];
  }
}

async function getTrendingRepos(sentRepos) {
  const now = new Date();
  const weekAgo = new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
  const monthAgo = new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

  const categories = {
    "🤖 AI & LLM": `topic:llm pushed:>${weekAgo} stars:>100`,
    "🕹️ AI Agents": `topic:ai-agents stars:>50 pushed:>${weekAgo}`,
    "⚡ Dev Tools": `topic:developer-tools stars:>200 pushed:>${weekAgo}`,
    "🌐 Web & Frontend": `topic:typescript stars:>500 pushed:>${weekAgo}`,
    "🐍 Python Hot": `language:python created:>${monthAgo} stars:>100`,
    "🦀 Rust": `language:rust created:>${monthAgo} stars:>80`,
    "📱 Flutter": `topic:flutter pushed:>${weekAgo} stars:>200`,
    "🚀 Rising Stars": `created:>${weekAgo} stars:>30`,
  };

  const allRepos = [];
  const newRepos = [];

  for (const [category, query] of Object.entries(categories)) {
    const repos = await fetchRepos(query);
    for (const r of repos) {
      r._category = category;
      if (!sentRepos.has(r.full_name)) newRepos.push(r);
      allRepos.push(r);
    }
  }

  return newRepos.length > 0 ? newRepos : allRepos;
}

// ─── Hacker News fetcher ──────────────────────────────────────────────────────

async function getHackerNewsTop() {
  try {
    const idsRes = await axios.get(
      "https://hacker-news.firebaseio.com/v0/topstories.json",
      { timeout: 10000 }
    );
    const top15 = idsRes.data.slice(0, 15);

    const stories = await Promise.all(
      top15.map((id) =>
        axios
          .get(`https://hacker-news.firebaseio.com/v0/item/${id}.json`, { timeout: 5000 })
          .then((r) => r.data)
          .catch(() => null)
      )
    );

    return stories
      .filter((s) => s && s.title && s.score > 50)
      .slice(0, 8)
      .map((s) => `• ${s.title} (${s.score} pts) — ${s.url || "news.ycombinator.com"}`);
  } catch (err) {
    console.error("HN Error:", err.message);
    return [];
  }
}

// ─── Dev.to fetcher ───────────────────────────────────────────────────────────

async function getDevToArticles() {
  try {
    const res = await axios.get("https://dev.to/api/articles", {
      params: { top: 1, per_page: 6 },
      timeout: 10000,
    });
    return res.data
      .filter((a) => a.positive_reactions_count > 20)
      .slice(0, 5)
      .map((a) => `• ${a.title} (❤️${a.positive_reactions_count}) — ${a.tag_list?.join(", ")}`);
  } catch (err) {
    console.error("Dev.to Error:", err.message);
    return [];
  }
}

// ─── Reddit fetcher ───────────────────────────────────────────────────────────

async function getRedditTop(subreddit) {
  try {
    const res = await axios.get(`https://www.reddit.com/r/${subreddit}/top.json`, {
      params: { t: "day", limit: 5 },
      headers: { "User-Agent": "TechMorningBot/1.0" },
      timeout: 10000,
    });
    return res.data.data.children
      .map((p) => p.data)
      .filter((p) => p.score > 50)
      .slice(0, 4)
      .map((p) => `• ${p.title} (↑${p.score})`);
  } catch (err) {
    console.error(`Reddit Error [${subreddit}]:`, err.message);
    return [];
  }
}

// ─── arXiv AI papers fetcher ──────────────────────────────────────────────────

async function getArxivPapers() {
  try {
    const res = await axios.get("https://export.arxiv.org/api/query", {
      params: {
        search_query: "cat:cs.AI OR cat:cs.LG",
        sortBy: "submittedDate",
        sortOrder: "descending",
        max_results: 5,
      },
      timeout: 10000,
    });
    const entries = res.data.match(/<title>(.*?)<\/title>/g) || [];
    return entries
      .slice(1, 5) // bỏ title đầu là feed title
      .map((t) => `• ${t.replace(/<\/?title>/g, "").trim()}`);
  } catch (err) {
    console.error("arXiv Error:", err.message);
    return [];
  }
}

// ─── Report builder ───────────────────────────────────────────────────────────

async function buildReport(repos) {
  if (!repos.length) return null;

  const today = new Date(Date.now() + 7 * 60 * 60 * 1000).toLocaleDateString("vi-VN");

  const [hnStories, devToArticles, redditML, arxivPapers] = await Promise.all([
    getHackerNewsTop(),
    getDevToArticles(),
    getRedditTop("MachineLearning"),
    getArxivPapers(),
  ]);

  const repoContext = repos
    .slice(0, 12)
    .map(
      (r) =>
        `[${r._category}] ${r.full_name} (${r.stargazers_count}⭐) — ${r.description || "N/A"} [${r.language || "?"}]`
    )
    .join("\n");

  const fmt = (arr, fallback) => arr.length ? arr.join("\n") : fallback;

  const prompt = `
Bạn là chuyên gia công nghệ và Tech Journalist hàng đầu Việt Nam.
Tổng hợp toàn bộ dữ liệu bên dưới và viết bản tin buổi sáng chất lượng cao cho Developer.

=== GITHUB TRENDING ===
${repoContext}

=== HACKER NEWS TOP ===
${fmt(hnStories, "N/A")}

=== DEV.TO TRENDING ===
${fmt(devToArticles, "N/A")}

=== REDDIT r/MachineLearning TOP TODAY ===
${fmt(redditML, "N/A")}

=== ARXIV AI PAPERS MỚI NHẤT ===
${fmt(arxivPapers, "N/A")}

VIẾT BẢN TIN THEO ĐÚNG CẤU TRÚC NÀY (HTML cho Telegram):

🌅 <b>TECH MORNING BRIEF — ${today}</b>

🔥 <b>HOT TREND HÔM NAY</b>
(Tổng hợp 1 insight sắc nét nhất từ toàn bộ dữ liệu — 2-3 câu)

📰 <b>ĐIỂM TIN NÓNG</b>
(4-5 tin/bài nổi bật nhất từ HN + Dev.to + Reddit, mỗi dòng 1 câu tại sao dev cần đọc)

🚀 <b>GITHUB TRENDING</b>
(5-6 repo nổi bật:
• <b>ten/repo</b> ⭐N — <i>Tại sao quan trọng, 1 câu ngắn</i>)

🧬 <b>RESEARCH & AI PAPERS</b>
(2-3 paper arXiv đáng chú ý, giải thích ứng dụng thực tế của nó)

🔮 <b>XU HƯỚNG TƯƠNG LAI</b>
(3 tech/pattern đang nổi — cụ thể, actionable, không chung chung)

💡 <b>ACTION FOR DEVS</b>
(Gợi ý cụ thể: học gì, thử gì, build gì ngay hôm nay)

QUY TẮC BẮT BUỘC:
- Chỉ dùng HTML tags: <b>, <i>, <code>
- KHÔNG dùng Markdown
- Văn phong sắc sảo, thẳng thắn cho Developer
- Tối đa 3800 ký tự
- Viết bằng Tiếng Việt
`;

  try {
    const result = await groq.chat.completions.create({
      model: "llama-3.3-70b-versatile",
      messages: [{ role: "user", content: prompt }],
      max_tokens: 2000,
      temperature: 0.7,
    });
    return result.choices[0].message.content;
  } catch (err) {
    console.error("Groq Error:", err.message);
    return null;
  }
}

// ─── Telegram sender ──────────────────────────────────────────────────────────

async function sendTelegram(text) {
  // Tự cắt nếu vượt giới hạn 4096 ký tự của Telegram
  const chunks = text.match(/.{1,4000}/gs) || [text];
  for (const chunk of chunks) {
    await bot.sendMessage(process.env.CHAT_ID, chunk, {
      parse_mode: "HTML",
      disable_web_page_preview: true,
    });
  }
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function runBot() {
  const nowVN = new Date(Date.now() + 7 * 60 * 60 * 1000);
  const timeStr = nowVN.toLocaleString("vi-VN");

  console.log(`🚀 [${timeStr}] Đang quét GitHub trending...`);

  try {
    const sentRepos = loadSent();
    const repos = await getTrendingRepos(sentRepos);

    if (!repos.length) {
      await sendTelegram(`🕒 <code>${timeStr} ICT</code>\n⚠️ Không tìm thấy repo nào hôm nay.`);
      return;
    }

    const report = await buildReport(repos);

    if (!report) {
      await sendTelegram(`🕒 <code>${timeStr} ICT</code>\n⚠️ Gemini không thể phân tích hôm nay.`);
      return;
    }

    const header = `🕒 <code>${timeStr} ICT</code>\n\n`;
    await sendTelegram(header + report);

    const sentNames = repos.slice(0, 15).map((r) => r.full_name);
    sentNames.forEach((name) => sentRepos.add(name));
    saveSent(sentRepos);

    console.log(`✅ Đã gửi bản tin — ${sentNames.length} repos được đánh dấu.`);
  } catch (err) {
    console.error("❌ ERROR:", err.message);
    await sendTelegram(`❌ <b>Lỗi hệ thống:</b> <code>${err.message}</code>`);
  }
}

runBot();
