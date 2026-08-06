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

  // Div vacío que se va llenando con cada trozo de texto que llega
  const botMsg = addMessage("", "bot");
  botMsg.classList.add("typing-cursor"); // opcional: estilo de "cursor" mientras escribe
  let fullText = "";
  let gotAnyContent = false;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!response.ok || !response.body) {
      throw new Error("Respuesta no válida del servidor");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Los eventos SSE vienen separados por línea vacía ("\n\n")
      const parts = buffer.split("\n\n");
      buffer = parts.pop(); // guarda el fragmento incompleto para la próxima iteración

      for (const part of parts) {
        const lines = part.split("\n");
        let eventType = "message";
        let eventData = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            eventData = line.slice(6);
          }
        }

        if (eventType === "error") {
          botMsg.textContent = "⚠️ " + eventData;
          botMsg.classList.remove("typing-cursor");
          reader.cancel();
          return;
        }

        if (eventType === "done") {
          continue; // fin normal del stream
        }

        // Restaura los saltos de línea que escapamos en el backend
        fullText += eventData.replace(/\\n/g, "\n");
        gotAnyContent = true;
        botMsg.textContent = fullText;
        chatWindow.scrollTop = chatWindow.scrollHeight;
      }
    }

    if (!gotAnyContent) {
      botMsg.textContent = "⚠️ No se recibió respuesta del servidor.";
    }
  } catch (err) {
    botMsg.textContent = "⚠️ No se pudo conectar con el servidor.";
  } finally {
    botMsg.classList.remove("typing-cursor");
    sendBtn.disabled = false;
    userInput.focus();
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/history");
    const data = await response.json();

    if (data.messages && data.messages.length > 0) {
      chatWindow.innerHTML = ""; // quita el saludo inicial estático
      data.messages.forEach((m) => {
        addMessage(m.content, m.role === "user" ? "user" : "bot");
      });
    }
  } catch (err) {
    console.error("No se pudo cargar el historial:", err);
  }
}

loadHistory();

sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") sendMessage();
});

resetBtn.addEventListener("click", async () => {
  await fetch("/reset", { method: "POST" });
  chatWindow.innerHTML = "";
  addMessage("Conversación reiniciada. ¿En qué te ayudo?", "bot");
});
