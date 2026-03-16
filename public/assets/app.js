const messagesEl = document.getElementById("messages");
const formEl = document.getElementById("chat-form");
const queryEl = document.getElementById("query");
const sessionIdEl = document.getElementById("session-id");
const sessionIdLabelEl = document.getElementById("session-id-label");
const sendButtonEl = document.getElementById("send-button");
const streamToggleEl = document.getElementById("stream-toggle");
const statusEl = document.getElementById("service-status");
const statusDotEl = document.getElementById("status-dot");
const clearSessionEl = document.getElementById("clear-session");
const messageTemplateEl = document.getElementById("message-template");

const API_BASE =
  window.location.protocol === "http:" || window.location.protocol === "https:"
    ? window.location.origin
    : "http://127.0.0.1:8000";

if (window.marked) {
  window.marked.setOptions({
    breaks: true,
    gfm: true,
  });
}

function buildSessionId() {
  const suffix = Math.random().toString(36).slice(2, 8);
  return `demo-${suffix}`;
}

function renderMarkdown(text) {
  const raw = (text || "").trim();
  if (!raw) {
    return "";
  }

  if (window.marked && window.DOMPurify) {
    return window.DOMPurify.sanitize(window.marked.parse(raw));
  }

  return raw
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");
}

function createMessage(role, body, extraClass = "") {
  // Remove welcome messages on first interaction
  const welcomeMsg = messagesEl.querySelector(".welcome-message");
  if (welcomeMsg) {
    welcomeMsg.remove();
  }

  const node = messageTemplateEl.content.firstElementChild.cloneNode(true);
  node.classList.add(role);
  if (extraClass) {
    node.classList.add(extraClass);
  }
  
  // Set avatar content or style
  const bodyEl = node.querySelector(".message-body");
  bodyEl.innerHTML = renderMarkdown(body);
  
  messagesEl.appendChild(node);
  scrollToBottom();
  
  return node;
}

function updateMessage(node, body) {
  node.querySelector(".message-body").innerHTML = renderMarkdown(body);
  scrollToBottom();
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function updateSessionLabel() {
  sessionIdLabelEl.textContent = sessionIdEl.value.trim() || "demo-web";
}

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (response.ok) {
      statusEl.textContent = "运行中";
      statusDotEl.className = "status-dot online";
    } else {
      statusEl.textContent = "异常";
      statusDotEl.className = "status-dot offline";
    }
  } catch (error) {
    statusEl.textContent = "离线";
    statusDotEl.className = "status-dot offline";
  }
}

function setBusy(isBusy) {
  sendButtonEl.disabled = isBusy;
  if (!isBusy) {
    // Focus back on textarea if we just finished
    setTimeout(() => queryEl.focus(), 50);
  }
}

function parseSseChunk(rawChunk) {
  const lines = rawChunk.split("\n");
  const event = lines.find((line) => line.startsWith("event:"))?.slice(6).trim();
  const dataLine = lines.find((line) => line.startsWith("data:"));
  if (!event || !dataLine) {
    return null;
  }

  try {
    return {
      event,
      data: JSON.parse(dataLine.slice(5).trim()),
    };
  } catch (error) {
    return null;
  }
}

async function streamAnswer(query, sessionId) {
  const assistantMessage = createMessage("assistant", "<i class='ph ph-spinner ph-spin'></i> 正在思考中...");
  let answer = "";
  
  try {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, session_id: sessionId }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`请求失败，状态码 ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let started = false;

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const rawEvent of events) {
        const parsed = parseSseChunk(rawEvent);
        if (!parsed) {
          continue;
        }
        
        if (parsed.event === "token") {
          if (!started) {
            started = true;
            answer = ""; // Clear loader
          }
          answer += parsed.data.content || "";
          updateMessage(assistantMessage, answer);
        }
        
        if (parsed.event === "error") {
          throw new Error(parsed.data.message || "未知流式错误");
        }
      }
    }
  } catch (err) {
    updateMessage(assistantMessage, `请求失败：${err.message}`);
    assistantMessage.classList.add("error");
  }
}

async function requestAnswer(query, sessionId) {
  const assistantMessage = createMessage("assistant", "<i class='ph ph-spinner ph-spin'></i> 正在思考中...");
  try {
    const response = await fetch(`${API_BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, session_id: sessionId }),
    });
    
    if (!response.ok) {
      throw new Error(`请求失败，状态码 ${response.status}`);
    }

    const payload = await response.json();
    updateMessage(assistantMessage, payload.answer);
  } catch (err) {
    updateMessage(assistantMessage, `请求失败：${err.message}`);
    assistantMessage.classList.add("error");
  }
}

// Auto-resize textarea
queryEl.addEventListener("input", function() {
  this.style.height = "auto";
  this.style.height = (this.scrollHeight) + "px";
  // Enable/disable send button
  sendButtonEl.disabled = this.value.trim() === "";
});

// Handle enter key to send
queryEl.addEventListener("keydown", function(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    if (this.value.trim() !== "") {
      formEl.dispatchEvent(new Event("submit"));
    }
  }
});

formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryEl.value.trim();
  const sessionId = sessionIdEl.value.trim() || "demo-web";
  if (!query) {
    return;
  }

  updateSessionLabel();
  createMessage("user", query);
  
  queryEl.value = "";
  queryEl.style.height = "auto";
  setBusy(true);

  try {
    if (streamToggleEl.checked) {
      await streamAnswer(query, sessionId);
    } else {
      await requestAnswer(query, sessionId);
    }
  } finally {
    setBusy(false);
  }
});

document.querySelectorAll(".example-chip").forEach((button) => {
  button.addEventListener("click", () => {
    queryEl.value = button.dataset.query || "";
    queryEl.focus();
    sendButtonEl.disabled = false;
  });
});

clearSessionEl.addEventListener("click", async () => {
  if (!confirm("确定要清空当前会话记录吗？")) return;
  
  const sessionId = sessionIdEl.value.trim() || "demo-web";
  try {
    const response = await fetch(`${API_BASE}/sessions/${encodeURIComponent(sessionId)}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      throw new Error(`状态码 ${response.status}`);
    }
    messagesEl.innerHTML = `
      <div class="welcome-message">
        <div class="welcome-icon"><i class="ph-fill ph-chef-hat"></i></div>
        <h3>会话已重置</h3>
        <p>我们可以开始新的烹饪对话了。</p>
      </div>
    `;
  } catch (error) {
    createMessage("assistant", `清空会话失败：${error.message}`, "error");
  }
});

// Initialize
sessionIdEl.value = buildSessionId();
updateSessionLabel();
checkHealth();
queryEl.focus();
