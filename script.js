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

/**
 * Interpreta un bloque SSE ("event: ...\ndata: ...").
 * El backend serializa cada payload como JSON, por lo que los saltos de
 * línea y el código llegan intactos.
 */
function parseSSEBlock(block) {
  let eventType = "message";
  const dataLines = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).replace(/^ /, ""));
    }
  }

  const raw = dataLines.join("\n");
  let data;
  try {
    data = JSON.parse(raw);
  } catch {
    data = raw; // respaldo: texto plano
  }
  return { eventType, data };
}

async function sendMessage() {
  const text = userInput.value.trim();
  // Evita envíos duplicados (por ejemplo, con Enter mientras se espera la respuesta)
  if (!text || sendBtn.disabled) return;

  addMessage(text, "user");
  userInput.value = "";
  sendBtn.disabled = true;

  // Div vacío que se va llenando con cada trozo de texto que llega
  const botMsg = addMessage("", "bot");
  botMsg.classList.add("typing-cursor");
  let fullText = "";
  let gotAnyContent = false;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    if (!response.ok || !response.body) {
      let detail = "Respuesta no válida del servidor";
      try {
        const err = await response.json();
        if (err.error) detail = err.error;
      } catch { /* la respuesta no era JSON */ }
      throw new Error(detail);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Los eventos SSE vienen separados por una línea vacía ("\n\n")
      const parts = buffer.split("\n\n");
      buffer = parts.pop(); // guarda el fragmento incompleto para la próxima iteración

      for (const part of parts) {
        if (!part.trim()) continue;
        const { eventType, data } = parseSSEBlock(part);

        if (eventType === "error") {
          botMsg.textContent = "⚠️ " + data;
          reader.cancel();
          return;
        }

        if (eventType === "done") continue; // fin normal del stream

        fullText += data;
        gotAnyContent = true;
        botMsg.textContent = fullText;
        chatWindow.scrollTop = chatWindow.scrollHeight;
      }
    }

    if (!gotAnyContent) {
      botMsg.textContent = "⚠️ No se recibió respuesta del servidor.";
    }
  } catch (err) {
    botMsg.textContent = "⚠️ " + (err.message || "No se pudo conectar con el servidor.");
  } finally {
    botMsg.classList.remove("typing-cursor");
    sendBtn.disabled = false;
    userInput.focus();
  }
}

async function loadHistory() {
  try {
    const response = await fetch("/history");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();

    if (data.messages && data.messages.length > 0) {
      chatWindow.innerHTML = ""; // Limpia el saludo estático
      data.messages.forEach((m) => {
        addMessage(m.content, m.role === "user" ? "user" : "bot");
      });
    }
  } catch (err) {
    console.error("No se pudo cargar el historial:", err);
  }
}

// Carga el historial tan pronto como el DOM esté listo
document.addEventListener("DOMContentLoaded", loadHistory);

// Escuchadores de eventos para enviar mensaje y resetear
sendBtn.addEventListener("click", sendMessage);

userInput.addEventListener("keydown", (e) => {
  // isComposing evita enviar al confirmar texto con teclados IME
  if (e.key === "Enter" && !e.isComposing) sendMessage();
});

resetBtn.addEventListener("click", async () => {
  try {
    const response = await fetch("/reset", { method: "POST" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    chatWindow.innerHTML = "";
    addMessage("Conversación reiniciada. ¿En qué te ayudo?", "bot");
  } catch (err) {
    addMessage("⚠️ No se pudo reiniciar la conversación.", "bot");
  }
});
