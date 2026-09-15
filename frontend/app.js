const API_BASE = "http://127.0.0.1:8000";
const HISTORY_KEY = "minillm-chat-history";
const MAX_CONVERSATIONS = 5;

const messagesEl = document.getElementById("messages");
const emptyStateEl = document.getElementById("empty-state");
const formEl = document.getElementById("chat-form");
const inputEl = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const newChatBtn = document.getElementById("new-chat-btn");
const historyListEl = document.getElementById("history-list");

let conversations = [];
let currentConversationId = null;

function saveConversations() {
    try {
        const toSave = conversations.slice(0, MAX_CONVERSATIONS);
        localStorage.setItem(HISTORY_KEY, JSON.stringify(toSave));
    } catch (e) {
        // stockage indisponible ou plein : on continue sans persister
    }
}

function loadConversations() {
    try {
        const raw = localStorage.getItem(HISTORY_KEY);
        if (!raw) return [];
        const parsed = JSON.parse(raw);
        return Array.isArray(parsed) ? parsed.slice(0, MAX_CONVERSATIONS) : [];
    } catch (e) {
        return [];
    }
}

function createConversation() {
    const id = Date.now().toString();
    const conversation = { id, title: "Nouvelle conversation", messages: [] };
    conversations.unshift(conversation);
    if (conversations.length > MAX_CONVERSATIONS) {
        conversations = conversations.slice(0, MAX_CONVERSATIONS);
    }
    currentConversationId = id;
    renderHistory();
    renderMessages();
    saveConversations();
    return conversation;
}

function getCurrentConversation() {
    return conversations.find(c => c.id === currentConversationId);
}

function renderHistory() {
    historyListEl.innerHTML = "";
    conversations.forEach(conv => {
        const div = document.createElement("div");
        div.className = "history-item" + (conv.id === currentConversationId ? " active" : "");
        div.textContent = conv.title;
        div.addEventListener("click", () => {
            currentConversationId = conv.id;
            renderHistory();
            renderMessages();
        });
        historyListEl.appendChild(div);
    });
}

function renderMessages() {
    const conv = getCurrentConversation();
    messagesEl.innerHTML = "";

    if (!conv || conv.messages.length === 0) {
        messagesEl.appendChild(emptyStateEl);
        return;
    }

    conv.messages.forEach(msg => {
        messagesEl.appendChild(buildMessageEl(msg.role, msg.content));
        if (msg.sources && msg.sources.length > 0) {
            messagesEl.appendChild(buildSourcesEl(msg.sources));
        }
    });

    messagesEl.scrollTop = messagesEl.scrollHeight;
}

function buildMessageEl(role, content) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${role}`;

    const label = document.createElement("div");
    label.className = "role-label";
    label.textContent = role === "user" ? "toi" : "minillm";

    const contentEl = document.createElement("div");
    contentEl.className = "content";
    contentEl.textContent = content;

    wrapper.appendChild(label);
    wrapper.appendChild(contentEl);
    return wrapper;
}

function buildSourcesEl(sources) {
    const wrapper = document.createElement("div");
    wrapper.className = "sources";

    const label = document.createElement("div");
    label.className = "sources-label";
    label.textContent = "sources";
    wrapper.appendChild(label);

    sources.forEach((s, i) => {
        const row = document.createElement("div");
        row.className = "source-row";

        const idx = document.createElement("span");
        idx.className = "source-index";
        idx.textContent = `[${i + 1}]`;

        const link = document.createElement("a");
        link.href = s.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.textContent = s.title || s.url;

        row.appendChild(idx);
        row.appendChild(link);
        wrapper.appendChild(row);
    });

    return wrapper;
}

async function sendMessage(text) {
    let conv = getCurrentConversation();
    if (!conv) {
        conv = createConversation();
    }

    if (conv.messages.length === 0) {
        conv.title = text.slice(0, 40) + (text.length > 40 ? "…" : "");
    }

    conv.messages.push({ role: "user", content: text });
    renderHistory();
    renderMessages();
    saveConversations();

    sendBtn.disabled = true;

    const assistantMsg = { role: "assistant", content: "", sources: [] };
    conv.messages.push(assistantMsg);
    const assistantEl = buildMessageEl("assistant", "");
    messagesEl.appendChild(assistantEl);
    const assistantContentEl = assistantEl.querySelector(".content");
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const useProfileToggle = document.getElementById("use-profile-toggle");
        const useProfileContext = useProfileToggle ? useProfileToggle.checked : false;
        const forceSearchToggle = document.getElementById("force-search-toggle");
        const forceSearch = forceSearchToggle ? forceSearchToggle.checked : false;

        const response = await fetch(`${API_BASE}/api/chat/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                messages: conv.messages
                    .slice(0, -1)
                    .map(m => ({ role: m.role, content: m.content })),
                use_profile_context: useProfileContext,
                force_search: forceSearch,
            }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop();

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const dataStr = line.slice(6).trim();
                if (dataStr === "[DONE]") continue;

                try {
                    const data = JSON.parse(dataStr);
                    if (data.token) {
                        assistantMsg.content += data.token;
                        assistantContentEl.textContent = assistantMsg.content;
                        messagesEl.scrollTop = messagesEl.scrollHeight;
                    } else if (data.sources) {
                        assistantMsg.sources = data.sources;
                        const sourcesEl = buildSourcesEl(data.sources);
                        messagesEl.appendChild(sourcesEl);
                        messagesEl.scrollTop = messagesEl.scrollHeight;
                    } else if (data.error) {
                        assistantMsg.content += `\n[Erreur: ${data.error}]`;
                        assistantContentEl.textContent = assistantMsg.content;
                    }
                } catch (e) {
                    // ignore malformed chunks
                }
            }
        }
    } catch (err) {
        assistantMsg.content = `Erreur de connexion au backend : ${err.message}`;
        assistantContentEl.textContent = assistantMsg.content;
    } finally {
        sendBtn.disabled = false;
        saveConversations();
    }
}

formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;
    inputEl.value = "";
    inputEl.style.height = "auto";
    sendMessage(text);
});

inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        formEl.requestSubmit();
    }
});

inputEl.addEventListener("input", () => {
    inputEl.style.height = "auto";
    inputEl.style.height = inputEl.scrollHeight + "px";
});

newChatBtn.addEventListener("click", () => {
    createConversation();
});

conversations = loadConversations();
if (conversations.length > 0) {
    currentConversationId = conversations[0].id;
    renderHistory();
    renderMessages();
} else {
    createConversation();
}
