// Stores all dialogue history per role
const roleHistory = {
  pro: [],
  con: [],
  expert: [],
  observer: [],
  verdict: [] 
};

// Renders all five characters side by side with their latest message
function renderAllRoles() {
  const chatbox = document.getElementById("chatBox");
  chatbox.innerHTML = "";

  const roleImages = {
    pro: "/static/images/pro_role.png",
    con: "/static/images/con_role.png",
    expert: "/static/images/expert.png",
    observer: "/static/images/observer.png",
    verdict: "/static/images/verdict.png" // ✅ New image for Verdict
  };

  const container = document.createElement("div");
  container.className = "role-grid";

  Object.keys(roleHistory).forEach(role => {
    const wrapper = document.createElement("div");
    wrapper.className = "character-scene";

    const avatar = document.createElement("img");
    avatar.src = roleImages[role] || "/static/images/default.png";
    avatar.alt = role;
    avatar.className = "avatar-big";
    avatar.onerror = () => avatar.src = "/static/images/default.png";

    const bubble = document.createElement("div");
    bubble.className = "dialogue-bubble";
    const latestMsg = roleHistory[role].at(-1) || "...";

    bubble.innerHTML = `
      <div class="role-name">${capitalize(role)}</div>
      <div class="message-text">${latestMsg}</div>
    `;

    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
    container.appendChild(wrapper);
  });

  chatbox.appendChild(container);
  chatbox.scrollTop = chatbox.scrollHeight;
}

// Display combined full history
function showCombinedHistory() {
  const chatbox = document.getElementById("chatBox");
  chatbox.innerHTML = "";

  const wrapper = document.createElement("div");
  wrapper.className = "character-scene";

  const title = document.createElement("h3");
  title.textContent = "📄 Full Debate History";
  title.style.textAlign = "center";
  wrapper.appendChild(title);

  const list = document.createElement("ul");
  list.style.listStyle = "none";
  list.style.padding = "0";

  const combined = [];
  const rounds = Math.max(...Object.values(roleHistory).map(arr => arr.length));

  for (let i = 0; i < rounds; i++) {
    for (const role of ["pro", "con", "expert", "observer", "verdict"]) {
      if (roleHistory[role][i]) {
        combined.push({ role, msg: roleHistory[role][i] });
      }
    }
  }

  combined.forEach((entry, index) => {
    const item = document.createElement("li");
    item.className = "history-bubble";
    item.innerHTML = `<strong>Round ${Math.floor(index / 5) + 1} [${capitalize(entry.role)}]:</strong> ${entry.msg}`;
    list.appendChild(item);
  });

  const backBtn = document.createElement("button");
  backBtn.textContent = "🔙 Back to Dialogue";
  backBtn.style.marginTop = "20px";
  backBtn.onclick = () => renderAllRoles();

  wrapper.appendChild(list);
  wrapper.appendChild(backBtn);
  chatbox.appendChild(wrapper);
  chatbox.scrollTop = 0;
}

// Starts the debate and updates all roles per round
async function startDebate() {
  const topic = document.getElementById("topicInput").value.trim();
  const rounds = parseInt(document.getElementById("roundInput").value);
  if (!topic) return alert("Please enter a topic.");
  if (isNaN(rounds) || rounds <= 0) return alert("Invalid round count.");

  Object.keys(roleHistory).forEach(r => roleHistory[r] = []);
  await fetch('/reset', { method: "POST" });

  for (let i = 0; i < rounds * 5; i++) { // 5 roles now
    const res = await fetch("/debate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic })
    });

    const data = await res.json();
    const roleKey = data.role?.toLowerCase();
    if (data.reply && roleHistory[roleKey]) {
      roleHistory[roleKey].push(data.reply);
    }

    renderAllRoles();
    await new Promise(resolve => setTimeout(resolve, 800));
  }

  alert("Debate completed!");
}

// Capitalize first letter utility
function capitalize(word) {
  return word.charAt(0).toUpperCase() + word.slice(1);
}
