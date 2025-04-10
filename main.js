document.addEventListener("DOMContentLoaded", function () {
  const sendButton = document.getElementById("sendButton");
  const userInput = document.getElementById("userInput");
  const chatbox = document.getElementById("chatbox");
  const debateButton = document.getElementById("debateButton");
  const topicInput = document.getElementById("topicInput");
  const roundInput = document.getElementById("roundInput");

  // Send chat message
  sendButton.addEventListener("click", function (event) {
    event.preventDefault();
    sendMessage();
  });

  // Start debate logic
  debateButton.addEventListener("click", function (event) {
    event.preventDefault();
    startDebate();
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
    const rounds = parseInt(roundInput.value) || 6; // Use 6 if invalid

    if (!topic) return;

    fetch('/reset', { method: "POST" });

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

  // Show bubble message
  function appendMessage(role, msg) {
    const bubble = document.createElement("div");
    const safeRole = (role || "unknown").toLowerCase();
    bubble.className = `bubble ${safeRole}`;
    bubble.innerHTML = `<strong>${role || "Unknown"}:</strong><br>${msg}`;
    chatbox.appendChild(bubble);
    chatbox.scrollTop = chatbox.scrollHeight;
  }
});

  