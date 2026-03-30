import axios from "axios";
import TelegramBot from "node-telegram-bot-api";
import dotenv from "dotenv";

dotenv.config();

const bot = new TelegramBot(process.env.TELEGRAM_TOKEN);
const headers = { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` };

// 🔹 1. Lấy Repo đang "Hot" trong 7 ngày qua
async function getTrendingRepos() {
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  const dateStr = sevenDaysAgo.toISOString().split('T')[0];

  const res = await axios.get("https://api.github.com/search/repositories", {
    params: {
      // Tìm các repo AI/LLM tạo trong 7 ngày qua, có từ 50 star trở lên
      q: `(ai OR llm OR agent OR "claude code" OR "gemini") created:>${dateStr} stars:>50`,
      sort: "stars",
      order: "desc",
      per_page: 8,
    },
    headers,
  });
  return res.data.items;
}

// 🔹 2. AI Helper với System Prompt nghiêm ngặt
async function askAI(prompt) {
  try {
    const res = await axios.post(
      "https://api.groq.com/openai/v1/chat/completions",
      {
        model: "llama-3.3-70b-versatile",
        messages: [
          {
            role: "system",
            content: "Bạn là chuyên gia phân tích công nghệ. Chỉ dựa trên dữ liệu được cung cấp, không tự chế tên dự án hay số liệu. Trả lời bằng tiếng Việt, ngắn gọn, súc tích."
          },
          { role: "user", content: prompt },
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
    return "⚠️ Không thể phân tích xu hướng lúc này.";
  }
}

// 🔹 3. Xây dựng bản tin
async function buildMessage() {
  const repos = await getTrendingRepos();
  if (repos.length === 0) return "Chưa tìm thấy trend mới nào trong 7 ngày qua.";

  // Chuẩn bị dữ liệu sạch cho AI
  const repoDataForAI = repos.map(r => 
    `- ${r.full_name}: ${r.description} (${r.stargazers_count} stars)`
  ).join("\n");

  // Gọi AI xử lý các phần
  const [highlight, insight, deepDive] = await Promise.all([
    askAI(`Tóm tắt 1 xu hướng công nghệ nổi bật nhất từ danh sách này (tối đa 2 câu):\n${repoDataForAI}`),
    askAI(`Viết 1 lời khuyên hoặc insight ngắn cho lập trình viên từ các repo này (1 câu):\n${repoDataForAI}`),
    askAI(`Phân loại các repo này thành các nhóm (ví dụ: AI Agents, Developer Tools...). Trả lời dạng bullet point:\n${repoDataForAI}`)
  ]);

  // Xây dựng danh sách Top Repos (giữ nguyên số liệu thực tế từ GitHub)
  let topReposList = "";
  for (const r of repos.slice(0, 5)) {
    topReposList += `• <a href="${r.html_url}">${r.full_name}</a> ⭐ ${r.stargazers_count}\n  └ ${r.description || "No description"}\n\n`;
  }

  const today = new Date().toLocaleDateString('vi-VN');

  return `
⚡ <b>AI Trend Hunter — Daily Brief (${today})</b>

🔥 <b>TIÊU ĐIỂM</b>
${highlight}

🚀 <b>TOP NEW TRENDING (7 DAYS)</b>
${topReposList}

💡 <b>INSIGHT</b>
<i>${insight}</i>

📚 <b>PHÂN LOẠI</b>
${deepDive}

#AITrend #GitHubTrending #TechUpdate
`;
}

// 🔹 4. Run
async function runBot() {
  try {
    console.log("🚀 Đang săn lùng trend mới...");
    const text = await buildMessage();
    
    await bot.sendMessage(process.env.CHAT_ID, text, { parse_mode: 'HTML' });
    console.log("✅ Đã gửi bản tin thực tế lên Telegram!");
  } catch (err) {
    console.error("❌ ERROR:", err.message);
  }
}

runBot();
