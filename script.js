const chatWindow = document.getElementById("chat-window");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const resetBtn = document.getElementById("reset-btn");

function addMessage(text, sender) {
  const msg = document.createElement("div");
  msg.className = `message ${sender}`;
  msg.textContent = text;
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return msg;
}

async function sendMessage() {
  const text = userInput.value.trim();
  if (!text) return;

  addMessage(text, "user");
  userInput.value = "";
  sendBtn.disabled = true;

  const typingMsg = addMessage("Escribiendo...", "bot typing");

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    const data = await response.json();
    typingMsg.remove();

    if (data.error) {
      addMessage("⚠️ " + data.error, "bot");
    } else {
      addMessage(data.reply, "bot");
    }
  } catch (err) {
    typingMsg.remove();
    addMessage("⚠️ No se pudo conectar con el servidor.", "bot");
  } finally {
    sendBtn.disabled = false;
    userInput.focus();
  }
}

sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

resetBtn.addEventListener("click", async () => {
  await fetch("/reset", { method: "POST" });
  chatWindow.innerHTML = "";
  addMessage("Conversación reiniciada. ¿En qué te ayudo?", "bot");
});
