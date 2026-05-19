/* static/main.js */
const STORAGE_THREAD_KEY = "ai_chief_current_thread";
const STORAGE_RECENT_COLLAPSED_KEY = "ai_chief_recent_collapsed";

let sessionMetas = {};
let currentThreadId = localStorage.getItem(STORAGE_THREAD_KEY) || null;
let recentCollapsed = localStorage.getItem(STORAGE_RECENT_COLLAPSED_KEY) === "1";

const toggleSidebarBtn = document.getElementById("toggle-sidebar-btn");
const mobileOverlay = document.getElementById("mobile-overlay");
const chatContainer = document.getElementById("chat-container");
const sessionListEl = document.getElementById("session-list");
const messageInput = document.getElementById("message-input");
const fileInput = document.getElementById("file-input");
const sendButton = document.getElementById("send-button");
const fileBadge = document.getElementById("file-badge");
const newChatBtn = document.getElementById("new-chat-btn");
const recentToggle = document.getElementById("recent-toggle");

marked.setOptions({ breaks: true, gfm: true });

function isMobile() {
    return window.innerWidth <= 768;
}

function updateSidebarState(open) {
    document.body.classList.toggle("sidebar-open", open);
    document.body.classList.toggle("sidebar-collapsed", !open);
}

function saveCurrentThread() {
    localStorage.setItem(STORAGE_THREAD_KEY, currentThreadId || "");
}

function updateRecentSectionState() {
    sessionListEl.classList.toggle("hidden", recentCollapsed);
    recentToggle.classList.toggle("collapsed", recentCollapsed);
    localStorage.setItem(STORAGE_RECENT_COLLAPSED_KEY, recentCollapsed ? "1" : "0");
}

function deriveSessionTitle(text, hasImage) {
    const cleaned = (text || "").replace(/\s+/g, " ").trim();
    if (cleaned) {
        return cleaned.slice(0, 12);
    }
    return hasImage ? "图片识别" : "新会话";
}

function enhanceRenderedContent(container) {
    const images = container.querySelectorAll("img");
    images.forEach((img) => {
        img.addEventListener("error", () => {
            if (img.dataset.brokenHandled === "1") return;
            img.dataset.brokenHandled = "1";
            const src = img.getAttribute("src") || "";
            const note = document.createElement("div");
            note.className = "broken-image-note";
            note.innerHTML = src
                ? `图片加载失败，可改为打开链接查看：<a href="${src}" target="_blank" rel="noopener noreferrer">${src}</a>`
                : "图片加载失败。";
            img.replaceWith(note);
        });
    });
}

function compactMarkdown(text) {
    return (text || "")
        .replace(/\r\n/g, "\n")
        .replace(/\n{3,}/g, "\n\n")
        .replace(/\n+(#{1,4}\s)/g, "\n\n$1")
        .replace(/(#{1,4}[^\n]*)\n{2,}/g, "$1\n")
        .replace(/\n{2,}([-*]\s)/g, "\n$1")
        .trim();
}

function renderEmptyState() {
    chatContainer.innerHTML = `
        <div class="empty-state">
            <div class="empty-card">
                <img src="/static/%E5%88%80%E5%8F%89.png" alt="刀叉">
                <h2>上传图片开始吧</h2>
                <p>我会帮您识别食材并推荐食谱</p>
            </div>
        </div>
    `;
}

function jumpChatToBottom() {
    const previous = chatContainer.style.scrollBehavior;
    chatContainer.style.scrollBehavior = "auto";
    chatContainer.scrollTop = chatContainer.scrollHeight;
    chatContainer.style.scrollBehavior = previous;
}

function moveSessionToTop(threadId) {
    if (!threadId || !sessionMetas[threadId]) {
        return;
    }

    const session = sessionMetas[threadId];
    const reordered = { [threadId]: session };
    Object.keys(sessionMetas).forEach((id) => {
        if (id !== threadId) {
            reordered[id] = sessionMetas[id];
        }
    });
    sessionMetas = reordered;
}

function isCurrentSessionEmptyNew() {
    const hasMessages = Boolean(chatContainer.querySelector(".message-wrapper"));
    return Boolean(currentThreadId)
        && sessionMetas[currentThreadId]?.title === "新会话"
        && !hasMessages;
}

function createNewSession() {
    if (isCurrentSessionEmptyNew()) {
        return;
    }

    const newId = "thread_" + Math.random().toString(36).slice(2, 10);
    sessionMetas[newId] = { title: "新会话" };
    currentThreadId = newId;
    moveSessionToTop(newId);
    saveCurrentThread();
    renderSessionList();
    renderEmptyState();
    if (isMobile()) updateSidebarState(false);
}

function escapeHtml(value) {
    return (value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll("\"", "&quot;")
        .replaceAll("'", "&#39;");
}

function renderSessionList() {
    sessionListEl.innerHTML = "";
    Object.keys(sessionMetas).forEach((id) => {
        const item = document.createElement("div");
        item.className = `session-item ${id === currentThreadId ? "active" : ""}`;
        item.innerHTML = `
            <div class="session-main" data-session-id="${id}">
                <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="16" width="16" aria-hidden="true">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span class="session-title">${escapeHtml(sessionMetas[id].title || "新会话")}</span>
            </div>
            <button class="delete-session-btn" type="button" data-delete-id="${id}" title="删除会话">
                <svg stroke="currentColor" fill="none" stroke-width="2" viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round" height="15" width="15" aria-hidden="true">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        `;
        sessionListEl.appendChild(item);
    });
    updateRecentSectionState();
}

async function switchSession(id) {
    if (currentThreadId === id) return;
    currentThreadId = id;
    saveCurrentThread();
    renderSessionList();
    await loadAndRenderHistory(id);
    if (isMobile()) updateSidebarState(false);
}

async function deleteSession(id) {
    if (!confirm("确定要删除这个会话的全部记录吗？")) return;

    try {
        await fetch("/history/" + id, { method: "DELETE" });
    } catch (error) {
        console.error("删除后端记录失败:", error);
    }

    delete sessionMetas[id];

    if (Object.keys(sessionMetas).length === 0) {
        currentThreadId = null;
        saveCurrentThread();
        createNewSession();
        return;
    }

    if (currentThreadId === id) {
        currentThreadId = Object.keys(sessionMetas)[0];
    }

    saveCurrentThread();
    renderSessionList();
    await loadAndRenderHistory(currentThreadId);
}

async function loadAndRenderHistory(id) {
    chatContainer.innerHTML = "";
    appendMessageUI("bot", "正在加载历史对话中...");

    try {
        const response = await fetch("/history/" + id);
        const data = await response.json();
        chatContainer.innerHTML = "";

        if (data.status === "success" && Array.isArray(data.messages) && data.messages.length > 0) {
            data.messages.forEach((msg) => {
                appendMessageUI(
                    msg.role === "user" ? "user" : "bot",
                    msg.content,
                    msg.image_url || null,
                    false
                );
            });
            jumpChatToBottom();
        } else {
            renderEmptyState();
        }
    } catch (error) {
        chatContainer.innerHTML = "";
        appendMessageUI("bot", "拉取历史对话失败，可能是后端服务未启动。");
        console.error(error);
    }
}

function appendMessageUI(role, content, imgUrl = null, autoScroll = true) {
    const emptyState = chatContainer.querySelector(".empty-state");
    if (emptyState) emptyState.remove();

    const isBot = role === "bot" || role === "assistant";
    const wrapper = document.createElement("div");
    wrapper.className = `message-wrapper ${isBot ? "bot" : "user"}`;

    const safeContent = typeof content === "string" ? content : String(content ?? "");
    const textHtml = isBot
        ? marked.parse(compactMarkdown(safeContent || "正在思考中..."))
        : escapeHtml(safeContent);
    const imageHtml = imgUrl ? `<br><img src="${imgUrl}" class="image-preview" alt="上传图片预览">` : "";

    wrapper.innerHTML = `
        <div class="message-content">
            <div class="avatar ${isBot ? "bot-avatar" : "user-avatar"}">${isBot ? "AI" : "U"}</div>
            <div class="text">${textHtml}${imageHtml}</div>
        </div>
    `;

    chatContainer.appendChild(wrapper);
    enhanceRenderedContent(wrapper);
    if (autoScroll) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    return wrapper;
}

async function initializeSessions() {
    try {
        const response = await fetch("/sessions");
        const data = await response.json();

        sessionMetas = {};
        if (data.status === "success" && Array.isArray(data.sessions)) {
            data.sessions.forEach((session) => {
                if (!session?.thread_id) return;
                sessionMetas[session.thread_id] = { title: session.title || session.thread_id };
            });
        }
    } catch (error) {
        sessionMetas = {};
        console.error("加载会话列表失败:", error);
    }

    const ids = Object.keys(sessionMetas);

    if (ids.length === 0) {
        createNewSession();
        return;
    }

    if (!currentThreadId || !sessionMetas[currentThreadId]) {
        currentThreadId = ids[0];
    }

    saveCurrentThread();
    renderSessionList();
    await loadAndRenderHistory(currentThreadId);
}

async function sendMessage() {
    const text = messageInput.value.trim();
    const file = fileInput.files[0];

    if (!text && !file) return;

    let imgBase64ForUI = null;
    if (file) {
        imgBase64ForUI = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (event) => resolve(event.target.result);
            reader.readAsDataURL(file);
        });
    }

    if (sessionMetas[currentThreadId] && sessionMetas[currentThreadId].title === "新会话") {
        sessionMetas[currentThreadId].title = deriveSessionTitle(text, Boolean(file));
        renderSessionList();
    }

    appendMessageUI("user", text || "上传了一张图片", imgBase64ForUI);

    messageInput.value = "";
    fileInput.value = "";
    fileBadge.style.display = "none";
    fileBadge.textContent = "";
    messageInput.disabled = true;
    sendButton.disabled = true;

    const formData = new FormData();
    formData.append("message", text);
    formData.append("thread_id", currentThreadId);
    if (file) formData.append("image", file);

    try {
        moveSessionToTop(currentThreadId);
        renderSessionList();

        const messageWrapper = appendMessageUI("bot", "正在识别食材并整理推荐...");
        const textContainer = messageWrapper.querySelector(".text");

        const response = await fetch("/chat", {
            method: "POST",
            body: formData
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let fullText = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            if (chunk) {
                fullText += chunk;
                textContainer.innerHTML = marked.parse(compactMarkdown(fullText));
                enhanceRenderedContent(messageWrapper);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
        }
    } catch (error) {
        appendMessageUI("bot", "发送失败，请检查网络或确认后端服务是否正常运行。");
        console.error(error);
    } finally {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
}

toggleSidebarBtn.addEventListener("click", () => {
    updateSidebarState(document.body.classList.contains("sidebar-collapsed"));
});

mobileOverlay.addEventListener("click", () => {
    if (isMobile()) updateSidebarState(false);
});

recentToggle.addEventListener("click", () => {
    recentCollapsed = !recentCollapsed;
    updateRecentSectionState();
});

newChatBtn.addEventListener("click", createNewSession);

sessionListEl.addEventListener("click", async (event) => {
    const deleteTarget = event.target.closest("[data-delete-id]");
    if (deleteTarget) {
        await deleteSession(deleteTarget.dataset.deleteId);
        return;
    }

    const switchTarget = event.target.closest("[data-session-id]");
    if (switchTarget) {
        await switchSession(switchTarget.dataset.sessionId);
    }
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        fileBadge.style.display = "inline-flex";
        fileBadge.textContent = fileInput.files[0].name;
    } else {
        fileBadge.style.display = "none";
        fileBadge.textContent = "";
    }
});

messageInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") sendMessage();
});

sendButton.addEventListener("click", sendMessage);

window.addEventListener("resize", () => {
    updateSidebarState(!isMobile());
});

updateSidebarState(!isMobile());
updateRecentSectionState();
initializeSessions();
