import axios from "axios";
import TelegramBot from "node-telegram-bot-api";
import dotenv from "dotenv";

dotenv.config();

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN);

// 🔹 GitHub headers
const headers = {
  Authorization: `Bearer ${process.env.GITHUB_TOKEN}`,
};

// 🔹 1. Lấy repo (có keyword nâng cấp)
async function getRepos() {
  const res = await axios.get(
    "https://api.github.com/search/repositories",
    {
      params: {
        q: "ai OR gpt OR claude OR llm OR agent created:>2024-01-01 stars:>50",
        sort: "stars",
        order: "desc",
        per_page: 10,
      },
      headers,
    }
  );

  return res.data.items;
}

// 🔹 2. AI helper (Groq)
async function askAI(prompt) {
  try {
    const res = await axios.post(
      "https://api.groq.com/openai/v1/chat/completions",
      {
        model: "llama-3.3-70b-versatile",
        messages: [
          {
            role: "user",
            content: prompt,
          },
        ],
      },
      {
        headers: {
          Authorization: `Bearer ${process.env.GROQ_API_KEY}`,
          "Content-Type": "application/json",
        },
      }
    );

    return res.data.choices[0].message.content;
  } catch (err) {
    console.error("AI ERROR:", err.response?.data || err.message);
    return "⚠️ AI error";
  }
}

// 🔹 3. Build message
async function buildMessage() {
  const repos = await getRepos();

  const filtered = repos.filter((r) => r.description);

  const repoText = filtered
    .map(
      (r) =>
        `${r.full_name} (${r.stargazers_count}⭐): ${r.description}`
    )
    .join("\n");

  // 🔥 TIÊU ĐIỂM
  const highlight = await askAI(
    `Tóm tắt xu hướng công nghệ từ các repo sau (2 câu):\n${repoText}`
  );

  // 💡 INSIGHT
  const insight = await askAI(
    `Viết 1 insight ngắn cho dev (2 câu max):\n${repoText}`
  );

  // 📚 DEEP DIVE
  const deepDive = await askAI(
    `Phân loại repo thành nhóm (AI Agents, Tools, UI...). Format bullet:\n${repoText}`
  );

  // 🚀 TOP repos
  let top = "";
  for (const r of filtered.slice(0, 5)) {
    const sum = await askAI(
      `Tóm tắt repo này trong 1 câu:\n${r.full_name} - ${r.description}`
    );

    top += `• ${r.full_name} ⭐ ${r.stargazers_count}\n  ${sum}\n\n`;
  }

  return `
⚡ AI Trend Hunter — Daily Brief

🔥 TIÊU ĐIỂM
${highlight}

🚀 TOP GITHUB TRENDING
${top}

💡 INSIGHT
${insight}

📚 DEEP DIVE
${deepDive}
`;
}

// 🔹 4. Run bot (single run)
async function runBot() {
  try {
    console.log("🚀 Running bot...");

    const text = await buildMessage();

    await bot.sendMessage(process.env.CHAT_ID, text);

    console.log("✅ Sent to Telegram!");
  } catch (err) {
    console.error("❌ ERROR:", err);
  }
}

runBot();
