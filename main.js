document.addEventListener("DOMContentLoaded", function () {
  const sendButton = document.getElementById("sendButton");
  const userInput = document.getElementById("userInput");
  const chatbox = document.getElementById("chatbox");
  const debateButton = document.getElementById("debateButton");
  const topicInput = document.getElementById("topicInput");
  const roundInput = document.getElementById("roundInput");
  const modeSelect = document.getElementById("modeSelect");

  // Default mode is "debate"
  let currentMode = "debate"; 

  // Mode switch logic
  modeSelect.addEventListener("change", function () {
    currentMode = modeSelect.value;
    console.log("Switched to mode:", currentMode);
  });

  // Send chat message (works in Chat Mode)
  sendButton.addEventListener("click", function (event) {
    event.preventDefault();
    if (currentMode === "chat") {
      sendMessage();
    } else {
      alert("Please switch to Chat Mode.");
    }
  });

  // Start debate (works in Debate Mode)
  debateButton.addEventListener("click", function (event) {
    event.preventDefault();
    if (currentMode === "debate") {
      startDebate();
    } else {
      alert("Please switch to Debate Mode.");
    }
  });

  function sendMessage() {
    var message = userInput.value.trim();
    if (message === '') return;

    appendMessage("user", message);

    fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: "user", message: message })
    })
    .then(response => response.json())
    .then(data => {
      appendMessage("assistant", data.reply);
      userInput.value = '';
      chatbox.scrollTop = chatbox.scrollHeight;
    })
    .catch(error => {
      console.error('Error:', error);
    });
  }

  // Debate sequence
  function startDebate() {
    const topic = topicInput.value.trim();
    const rounds = parseInt(roundInput.value) || 6; // Default to 6 rounds if input is invalid

    if (!topic) return;

    fetch('/reset', { method: "POST" }); // Reset previous data before starting a new debate

    for (let i = 0; i < rounds; i++) {
      fetch("/debate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic })
      })
      .then(response => response.json())
      .then(data => {
        appendMessage(data.role, data.reply);
      })
      .catch(error => {
        console.error("Error:", error);
      });
    }
  }

  // Show bubble message in the chat
  function appendMessage(role, msg) {
    const bubble = document.createElement("div");
    const safeRole = (role || "unknown").toLowerCase();
    bubble.className = `bubble ${safeRole}-bubble`;
    bubble.innerHTML = `<strong>${role || "Unknown"}:</strong><br>${msg}`;
    chatbox.appendChild(bubble);
    chatbox.scrollTop = chatbox.scrollHeight;
  }
});