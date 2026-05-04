/**
 * LeadMind AI — Chatbot Widget v1.0
 * Drop this in your site's <head> or <body> with:
 *   <script src="https://your-domain/public/sdk/chatbot-widget.js"
 *           data-api-key="lm_live_xxx"
 *           data-api-host="https://your-domain"
 *           data-title="Chat with us"
 *           data-color="#7C3AED"
 *           async></script>
 */
(function () {
  "use strict";

  var script = document.currentScript ||
    document.querySelector('script[data-api-key][src*="chatbot-widget"]');
  if (!script) return;

  var API_KEY  = script.getAttribute("data-api-key") || "";
  var API_HOST = (script.getAttribute("data-api-host") || "http://localhost:8000").replace(/\/$/, "");
  var TITLE    = script.getAttribute("data-title") || "LeadMind Assistant";
  var COLOR    = script.getAttribute("data-color") || "#7C3AED";
  var ENDPOINT = API_HOST + "/api/chat/message";

  // Generate or load session ID
  var SESSION_KEY = "lm_chat_session_" + API_KEY.slice(-8);
  var sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = "vis_" + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  // ── State ────────────────────────────────────────────────────────────────
  var isOpen = false;
  var messages = []; // {role: "user"|"assistant", text: str}

  // ── Inject CSS ────────────────────────────────────────────────────────────
  var style = document.createElement("style");
  style.textContent = [
    "#lm-widget{position:fixed;bottom:24px;right:24px;z-index:999999;font-family:system-ui,sans-serif}",
    "#lm-bubble{width:56px;height:56px;border-radius:50%;background:" + COLOR + ";display:flex;align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,0,.25);transition:transform .2s;border:2px solid rgba(255,255,255,.3)}",
    "#lm-bubble:hover{transform:scale(1.08)}",
    "#lm-bubble svg{width:26px;height:26px;fill:white}",
    "#lm-badge{position:absolute;top:-4px;right:-4px;width:18px;height:18px;border-radius:50%;background:#EF4444;color:#fff;font-size:10px;font-weight:700;display:none;align-items:center;justify-content:center;border:2px solid #fff}",
    "#lm-box{position:absolute;bottom:72px;right:0;width:340px;height:480px;background:#fff;border-radius:12px;box-shadow:0 12px 40px rgba(0,0,0,.18);display:none;flex-direction:column;overflow:hidden;border:1px solid rgba(0,0,0,.08)}",
    "#lm-header{background:" + COLOR + ";color:#fff;padding:14px 18px;font-weight:700;font-size:14px;display:flex;align-items:center;justify-content:space-between}",
    "#lm-header span{font-size:11px;opacity:.8;font-weight:400;margin-top:2px}",
    "#lm-close{background:none;border:none;color:#fff;opacity:.8;cursor:pointer;font-size:20px;padding:0;line-height:1}",
    "#lm-messages{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:#f8f8ff}",
    ".lm-msg{max-width:80%;padding:9px 13px;border-radius:10px;font-size:13px;line-height:1.5;word-break:break-word}",
    ".lm-msg.user{background:" + COLOR + ";color:#fff;align-self:flex-end;border-bottom-right-radius:3px}",
    ".lm-msg.assistant{background:#fff;color:#111;align-self:flex-start;border:1px solid #e5e5e5;border-bottom-left-radius:3px}",
    ".lm-typing{display:flex;gap:4px;padding:10px 13px;background:#fff;border:1px solid #e5e5e5;border-radius:10px;border-bottom-left-radius:3px;align-self:flex-start}",
    ".lm-typing span{width:6px;height:6px;border-radius:50%;background:#aaa;animation:lm-bounce 1.2s infinite}",
    ".lm-typing span:nth-child(2){animation-delay:.15s}.lm-typing span:nth-child(3){animation-delay:.3s}",
    "@keyframes lm-bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}",
    "#lm-input-row{display:flex;border-top:1px solid #e5e5e5;background:#fff;padding:8px}",
    "#lm-input{flex:1;border:none;outline:none;padding:8px 10px;font-size:13px;background:transparent;color:#111}",
    "#lm-send{background:" + COLOR + ";color:#fff;border:none;border-radius:8px;padding:8px 14px;cursor:pointer;font-weight:700;font-size:13px;transition:opacity .2s}",
    "#lm-send:hover{opacity:.85}",
    "#lm-status{font-size:10px;padding:4px 18px;background:" + COLOR + "22;color:" + COLOR + ";text-align:center;font-weight:600;display:none}",
  ].join("");
  document.head.appendChild(style);

  // ── Build DOM ─────────────────────────────────────────────────────────────
  var widget = document.createElement("div");
  widget.id = "lm-widget";
  widget.innerHTML = [
    '<div id="lm-bubble" role="button" aria-label="Open chat">',
      '<div id="lm-badge">1</div>',
      '<svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/></svg>',
    '</div>',
    '<div id="lm-box">',
      '<div id="lm-header">',
        '<div><div>' + TITLE + '</div><span>Powered by LeadMind AI</span></div>',
        '<button id="lm-close" aria-label="Close chat">&times;</button>',
      '</div>',
      '<div id="lm-status"></div>',
      '<div id="lm-messages"></div>',
      '<div id="lm-input-row">',
        '<input id="lm-input" placeholder="Type a message..." autocomplete="off"/>',
        '<button id="lm-send">Send</button>',
      '</div>',
    '</div>',
  ].join("");
  document.body.appendChild(widget);

  var bubble   = document.getElementById("lm-bubble");
  var box      = document.getElementById("lm-box");
  var badge    = document.getElementById("lm-badge");
  var msgsList = document.getElementById("lm-messages");
  var input    = document.getElementById("lm-input");
  var sendBtn  = document.getElementById("lm-send");
  var closeBtn = document.getElementById("lm-close");
  var statusBar= document.getElementById("lm-status");

  // ── Render helpers ────────────────────────────────────────────────────────
  function renderMsg(role, text) {
    var el = document.createElement("div");
    el.className = "lm-msg " + role;
    el.textContent = text;
    msgsList.appendChild(el);
    msgsList.scrollTop = msgsList.scrollHeight;
    return el;
  }

  function showTyping() {
    var el = document.createElement("div");
    el.className = "lm-typing";
    el.innerHTML = "<span></span><span></span><span></span>";
    el.id = "lm-typing-ind";
    msgsList.appendChild(el);
    msgsList.scrollTop = msgsList.scrollHeight;
  }

  function removeTyping() {
    var el = document.getElementById("lm-typing-ind");
    if (el) el.remove();
  }

  function setStatus(text) {
    if (text) {
      statusBar.textContent = text;
      statusBar.style.display = "block";
    } else {
      statusBar.style.display = "none";
    }
  }

  // ── Toggle ────────────────────────────────────────────────────────────────
  function openChat() {
    isOpen = true;
    box.style.display = "flex";
    badge.style.display = "none";
    input.focus();
    if (messages.length === 0) {
      // Greeting
      renderMsg("assistant", "Hi there! 👋 I'm the LeadMind AI assistant. How can I help you today?");
      messages.push({role: "assistant", text: "Hi there! 👋 I'm the LeadMind AI assistant. How can I help you today?"});
    }
  }

  function closeChat() {
    isOpen = false;
    box.style.display = "none";
  }

  bubble.addEventListener("click", function () { isOpen ? closeChat() : openChat(); });
  closeBtn.addEventListener("click", closeChat);

  // ── Send ──────────────────────────────────────────────────────────────────
  async function sendMessage() {
    var text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendBtn.disabled = true;

    renderMsg("user", text);
    messages.push({role: "user", text: text});
    showTyping();

    try {
      var resp = await fetch(ENDPOINT, {
        method: "POST",
        headers: {"Content-Type": "application/json", "X-Api-Key": API_KEY},
        body: JSON.stringify({session_id: sessionId, message: text})
      });
      removeTyping();
      if (resp.ok) {
        var data = await resp.json();
        renderMsg("assistant", data.reply);
        messages.push({role: "assistant", text: data.reply});
        if (data.lead_created) {
          setStatus("✅ You've been added to our follow-up list!");
          setTimeout(function(){setStatus("");}, 5000);
        }
      } else {
        renderMsg("assistant", "Sorry, I'm having trouble connecting. Please try again shortly.");
      }
    } catch (err) {
      removeTyping();
      renderMsg("assistant", "Connection error. Please try again later.");
    }
    sendBtn.disabled = false;
    input.focus();
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });

  // Show badge after 10 seconds if chat hasn't been opened
  setTimeout(function () {
    if (!isOpen) { badge.style.display = "flex"; }
  }, 10000);

})();
