// Global audio player state
let currentAudio = null;
let isPlaying = false;
let lastText = "";

// Stores all dialogue history per role
const roleHistory = {
  pro: [],
  con: [],
  expert: [],
  observer: [],
  verdict: [] 
};

// Renders all roles with latest messages and speaker buttons
function renderAllRoles() {
  const chatbox = document.getElementById("chatBox");
  chatbox.innerHTML = "";

  const roleImages = {
    pro: "/static/images/pro_role.png",
    con: "/static/images/con_role.png",
    expert: "/static/images/expert.png",
    observer: "/static/images/observer.png",
    verdict: "/static/images/verdict.png"
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

    const roleNameDiv = document.createElement("div");
    roleNameDiv.className = "role-name";
    roleNameDiv.innerText = capitalize(role);

    const speakBtn = document.createElement("button");
    speakBtn.className = "speak-btn";
    speakBtn.textContent = "🔊";
    speakBtn.title = "Play audio";
    speakBtn.addEventListener("click", () => speakText(latestMsg, role));

    roleNameDiv.appendChild(speakBtn);
    bubble.appendChild(roleNameDiv);

    const msgDiv = document.createElement("div");
    msgDiv.className = "message-text";
    msgDiv.innerText = latestMsg;

    bubble.appendChild(msgDiv);
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
    container.appendChild(wrapper);
  });

  chatbox.appendChild(container);
  chatbox.scrollTop = chatbox.scrollHeight;
}

// Text-to-speech: toggles playback/pause or fetches new audio
function speakText(text, role) {
  // If the same text is playing, pause it
  if (text === lastText && currentAudio && isPlaying) {
    currentAudio.pause();
    isPlaying = false;
    return;
  }

  // If the same text was paused, resume it
  if (text === lastText && currentAudio && !isPlaying) {
    currentAudio.play().catch(err => console.error("Resume error:", err));
    isPlaying = true;
    return;
  }

  // New text or different role → request new audio
  fetch("/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, role })
  })
    .then(res => res.json())
    .then(data => {
      currentAudio = new Audio(data.audio_url);
      currentAudio.play().then(() => {
        isPlaying = true;
        lastText = text;
      }).catch(err => {
        console.error("Play error:", err);
        isPlaying = false;
      });

      currentAudio.onended = () => {
        isPlaying = false;
        lastText = "";
      };
    })
    .catch(err => {
      console.error("TTS error:", err);
    });
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

  for (let i = 0; i < rounds * 5; i++) {
    const res = await fetch("/debate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, rounds })
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
