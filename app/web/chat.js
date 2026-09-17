const appShell = document.querySelector(".app-shell");
const sidebarToggle = document.querySelector("#sidebar-toggle");
const conversationListElement = document.querySelector("#conversation-list");
const messagesElement = document.querySelector("#messages");
const formElement = document.querySelector("#chat-form");
const inputElement = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const newChatButton = document.querySelector("#new-chat-button");
const statusElement = document.querySelector("#status-message");

const legacyConversationStorageKey = "northstar-it-assistant-conversation-id";
const conversationStorageKey = "fictional-it-assistant-conversation-id";
let conversationId;

function isSmallScreen() {
  return window.matchMedia("(max-width: 760px)").matches;
}

async function requestJson(url, options, errorMessage) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(errorMessage);
  }
  return response.json();
}

function migrateStoredConversationId() {
  const existingConversationId = localStorage.getItem(conversationStorageKey);
  const legacyConversationId = localStorage.getItem(legacyConversationStorageKey);
  if (!existingConversationId && legacyConversationId) {
    localStorage.setItem(conversationStorageKey, legacyConversationId);
  }
  localStorage.removeItem(legacyConversationStorageKey);
}

function addMessage(content, role) {
  const message = document.createElement("article");
  const paragraph = document.createElement("p");
  message.className = `message ${role}-message`;
  paragraph.textContent = content;
  message.append(paragraph);
  messagesElement.append(message);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

const toolMeta = {
  knowledge_search: { icon: "🔍", label: "Knowledge Search" },
  ticket_lookup: { icon: "🎫", label: "Ticket Lookup" },
  ticket_draft: { icon: "📝", label: "Ticket Draft" },
  ticket_creation: { icon: "🎟️", label: "Ticket Creation" },
  ticket_update: { icon: "🔄", label: "Ticket Update" },
};

function formatToolSummary(toolName, data) {
  if (!data || typeof data !== "object") return String(data || "Action completed");
  if (toolName === "knowledge_search") {
    const count = data.results?.length || 0;
    if (!count) return "No matching documents found in knowledge base.";
    const sources = [...new Set(data.results.map((r) => r.source_file).filter(Boolean))];
    return `Found ${count} relevant section${count > 1 ? "s" : ""} in ${sources.join(", ") || "knowledge base"}.`;
  }
  if (toolName === "ticket_lookup") {
    const tickets = data.tickets || [];
    if (!tickets.length) return "No matching support tickets found in database.";
    return `Found ${tickets.length} ticket${tickets.length > 1 ? "s" : ""}: ${tickets.map((t) => `${t.ticket_number} (${t.status})`).join(", ")}`;
  }
  if (toolName === "ticket_draft") {
    return `Prepared ticket draft: "${data.title || "Support Request"}" [${(data.priority || "medium").toUpperCase()}]`;
  }
  if (toolName === "ticket_creation") {
    if (data.ticket_number) {
      return `Created support ticket ${data.ticket_number} (${data.status || "open"})`;
    }
    if (data.duplicate_found) {
      const matchPct = data.match_score ? ` (${Math.round(data.match_score * 100)}% match)` : "";
      return `Duplicate ticket warning: Similar ticket ${data.existing_ticket?.ticket_number || ""} already exists${matchPct}.`;
    }
    return data.reason || "Ticket action completed.";
  }
  if (toolName === "ticket_update") {
    if (data.updated) {
      return `Updated ticket ${data.ticket_number} to ${(data.status || "updated").toUpperCase()}.`;
    }
    return data.reason || "Ticket update failed.";
  }
  return "Tool execution finished.";
}

function addToolActionMessage(toolName, rawContent) {
  const toolInfo = toolMeta[toolName] || { icon: "⚙️", label: toolName || "Tool Action" };
  let parsedData = null;
  try {
    parsedData = typeof rawContent === "string" ? JSON.parse(rawContent) : rawContent;
  } catch {
    parsedData = rawContent;
  }

  const card = document.createElement("article");
  card.className = "message tool-action-message";

  const header = document.createElement("div");
  header.className = "tool-action-header";

  const badge = document.createElement("span");
  badge.className = "tool-action-badge";
  badge.textContent = `${toolInfo.icon} ${toolInfo.label}`;

  const summary = document.createElement("span");
  summary.className = "tool-action-summary";
  summary.textContent = formatToolSummary(toolName, parsedData);

  header.append(badge, summary);
  card.append(header);

  if (rawContent) {
    const details = document.createElement("details");
    details.className = "tool-action-details";
    const detailsSummary = document.createElement("summary");
    detailsSummary.textContent = "View action details";
    const pre = document.createElement("pre");
    pre.textContent = typeof parsedData === "object" ? JSON.stringify(parsedData, null, 2) : String(rawContent);
    details.append(detailsSummary, pre);
    card.append(details);
  }

  messagesElement.append(card);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function addOpeningMessage(text = "Hello. I can help with VPN, password, MFA, Outlook, software access, and support tickets.") {
  addMessage(text, "assistant");
}

function addTypingIndicator() {
  const indicator = document.createElement("article");
  indicator.className = "message assistant-message typing-indicator";
  indicator.id = "typing-indicator";
  indicator.setAttribute("aria-label", "Assistant is working");
  indicator.innerHTML = "<span></span><span></span><span></span>";
  messagesElement.append(indicator);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function removeTypingIndicator() {
  document.querySelector("#typing-indicator")?.remove();
}

function removeTicketConfirmation() {
  document.querySelectorAll(".ticket-confirmation").forEach((element) => element.remove());
}

function showTicketConfirmation(ticket) {
  removeTicketConfirmation();
  const card = document.createElement("section");
  const details = document.createElement("dl");
  const confirmButton = document.createElement("button");
  card.className = "ticket-confirmation";
  card.innerHTML = "<h2>Review ticket before creation</h2><p>No ticket has been created yet.</p>";

  [
    ["Title", ticket.title],
    ["Description", ticket.description],
    ["Category", ticket.category],
    ["Priority", ticket.priority],
    ["Employee", ticket.employee_id || "Not provided"],
    ["Device", ticket.device_details || "Not provided"],
    ["Error", ticket.error_message || "Not provided"],
  ].forEach(([label, value]) => {
    const term = document.createElement("dt");
    const definition = document.createElement("dd");
    term.textContent = label;
    definition.textContent = value;
    details.append(term, definition);
  });

  confirmButton.className = "primary-button";
  confirmButton.type = "button";
  confirmButton.textContent = "Confirm and create ticket";
  confirmButton.addEventListener("click", async () => {
    confirmButton.disabled = true;
    await submitMessage("I confirm creation of the proposed ticket.");
  });
  card.append(details, confirmButton);
  messagesElement.append(card);
  messagesElement.scrollTop = messagesElement.scrollHeight;
}

function setSending(isSending) {
  inputElement.disabled = isSending;
  sendButton.disabled = isSending;
  sendButton.textContent = isSending ? "Sending..." : "Send";
}

function setActiveConversation(nextConversationId) {
  conversationId = nextConversationId;
  localStorage.setItem(conversationStorageKey, conversationId);
  document.querySelectorAll(".conversation-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.conversationId === conversationId);
  });
}

function formatConversationTime(value) {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

async function fetchConversations() {
  return requestJson("/conversations", undefined, "Unable to load conversations.");
}

function renderConversationList(conversations) {
  conversationListElement.innerHTML = "";

  if (!conversations.length) {
    const emptyMessage = document.createElement("p");
    emptyMessage.className = "empty-conversations";
    emptyMessage.textContent = "No saved chats yet.";
    conversationListElement.append(emptyMessage);
    return;
  }

  conversations.forEach((conversation) => {
    const item = document.createElement("article");
    item.role = "button";
    item.tabIndex = 0;
    item.className = "conversation-item";
    item.dataset.conversationId = conversation.conversation_id;
    item.classList.toggle("active", conversation.conversation_id === conversationId);

    const title = document.createElement("span");
    title.className = "conversation-title";
    title.textContent = conversation.title;

    const preview = document.createElement("span");
    preview.className = "conversation-preview";
    preview.textContent = conversation.last_message || "Start the conversation";

    const meta = document.createElement("span");
    meta.className = "conversation-meta";
    meta.textContent = `${conversation.message_count} messages - ${formatConversationTime(conversation.updated_at)}`;

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "conversation-delete";
    deleteButton.textContent = "Delete";
    deleteButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      await deleteConversation(conversation.conversation_id);
    });

    item.append(title, preview, meta, deleteButton);
    item.addEventListener("click", async () => {
      await openConversation(conversation.conversation_id);
      if (isSmallScreen()) {
        appShell.classList.add("sidebar-collapsed");
      }
    });
    item.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        await openConversation(conversation.conversation_id);
      }
    });

    conversationListElement.append(item);
  });
}

async function refreshConversationList() {
  const conversations = await fetchConversations();
  renderConversationList(conversations);
  return conversations;
}

async function deleteConversation(deletedConversationId) {
  await requestJson(
    `/conversations/${deletedConversationId}`,
    { method: "DELETE" },
    "Unable to delete the conversation.",
  );

  if (conversationId === deletedConversationId) {
    localStorage.removeItem(conversationStorageKey);
    conversationId = undefined;
  }

  const conversations = await refreshConversationList();
  if (conversationId) return;

  if (conversations.length) {
    await openConversation(conversations[0].conversation_id);
  } else {
    await startConversation();
  }
}

async function startConversation() {
  const data = await requestJson("/conversations", { method: "POST" }, "Unable to start a conversation.");

  setActiveConversation(data.conversation_id);
  messagesElement.innerHTML = "";
  addOpeningMessage("New conversation started. How can I help?");
  await refreshConversationList();
  statusElement.textContent = "Conversation ready.";
}

async function openConversation(nextConversationId) {
  const conversation = await requestJson(
    `/conversations/${nextConversationId}`,
    undefined,
    "Conversation was not found.",
  );

  setActiveConversation(conversation.conversation_id);
  messagesElement.innerHTML = "";
  removeTicketConfirmation();
  conversation.messages.forEach((message) => {
    if (message.role === "tool") {
      addToolActionMessage(message.tool_name, message.content);
    } else if (message.role === "user" || message.role === "assistant") {
      addMessage(message.content, message.role);
    }
  });
  if (!messagesElement.childElementCount) {
    addOpeningMessage();
  }
  if (conversation.pending_ticket) {
    showTicketConfirmation(conversation.pending_ticket);
  }
  statusElement.textContent = "Conversation ready.";
  await refreshConversationList();
}

async function sendMessage(message) {
  return requestJson(
    `/conversations/${conversationId}/messages`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    },
    "The assistant could not process that message. Please try again.",
  );
}

async function submitMessage(message) {
  addMessage(message, "user");
  setSending(true);
  statusElement.textContent = "Assistant is working...";
  addTypingIndicator();

  try {
    const result = await sendMessage(message);
    if (Array.isArray(result.tool_calls) && result.tool_calls.length) {
      result.tool_calls.forEach((tool) => {
        addToolActionMessage(tool.tool_name, tool.content);
      });
    }
    addMessage(result.response, "assistant");
    if (result.requires_confirmation && result.pending_ticket) {
      showTicketConfirmation(result.pending_ticket);
    } else {
      removeTicketConfirmation();
    }
    await refreshConversationList();
    statusElement.textContent = result.ticket_number
      ? `Ticket ${result.ticket_number} created.`
      : result.requires_confirmation
        ? "Review the proposed ticket and confirm creation."
        : result.requires_input
          ? "More information is needed."
          : "Conversation ready.";
  } catch (error) {
    addMessage(error.message, "assistant");
    statusElement.textContent = "Request failed.";
  } finally {
    removeTypingIndicator();
    setSending(false);
    inputElement.focus();
  }
}

async function bootstrap() {
  migrateStoredConversationId();
  const conversations = await refreshConversationList();
  const storedConversationId = localStorage.getItem(conversationStorageKey);
  const storedConversation = conversations.find((conversation) => conversation.conversation_id === storedConversationId);

  if (storedConversation) {
    await openConversation(storedConversation.conversation_id);
    return;
  }

  if (conversations.length) {
    await openConversation(conversations[0].conversation_id);
    return;
  }

  await startConversation();
}

formElement.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = inputElement.value.trim();
  if (!message || !conversationId) return;
  inputElement.value = "";
  await submitMessage(message);
});

inputElement.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    formElement.requestSubmit();
  }
});

newChatButton.addEventListener("click", async () => {
  setSending(true);
  try {
    await startConversation();
  } catch (error) {
    statusElement.textContent = error.message;
  } finally {
    setSending(false);
  }
});

sidebarToggle.addEventListener("click", () => {
  appShell.classList.toggle("sidebar-collapsed");
});

if (isSmallScreen()) {
  appShell.classList.add("sidebar-collapsed");
}

bootstrap().catch((error) => {
  statusElement.textContent = error.message;
});
