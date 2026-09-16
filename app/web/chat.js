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
  const response = await fetch("/conversations");
  if (!response.ok) {
    throw new Error("Unable to load conversations.");
  }
  return response.json();
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
    const item = document.createElement("button");
    const title = document.createElement("span");
    const preview = document.createElement("span");
    const meta = document.createElement("span");

    item.type = "button";
    item.className = "conversation-item";
    item.dataset.conversationId = conversation.conversation_id;
    item.classList.toggle("active", conversation.conversation_id === conversationId);

    title.className = "conversation-title";
    title.textContent = conversation.title;
    preview.className = "conversation-preview";
    preview.textContent = conversation.last_message || "Start the conversation";
    meta.className = "conversation-meta";
    meta.textContent = `${conversation.message_count} messages - ${formatConversationTime(conversation.updated_at)}`;

    item.append(title, preview, meta);
    item.addEventListener("click", async () => {
      await openConversation(conversation.conversation_id);
      if (window.matchMedia("(max-width: 760px)").matches) {
        appShell.classList.add("sidebar-collapsed");
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

async function startConversation() {
  const response = await fetch("/conversations", { method: "POST" });
  if (!response.ok) {
    throw new Error("Unable to start a conversation.");
  }
  const data = await response.json();
  setActiveConversation(data.conversation_id);
  messagesElement.innerHTML = "";
  addOpeningMessage("New conversation started. How can I help?");
  await refreshConversationList();
  statusElement.textContent = "Conversation ready.";
}

async function openConversation(nextConversationId) {
  const response = await fetch(`/conversations/${nextConversationId}`);
  if (!response.ok) {
    throw new Error("Conversation was not found.");
  }

  const conversation = await response.json();
  setActiveConversation(conversation.conversation_id);
  messagesElement.innerHTML = "";
  removeTicketConfirmation();
  conversation.messages
    .filter((message) => message.role === "user" || message.role === "assistant")
    .forEach((message) => addMessage(message.content, message.role));
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
  const response = await fetch(`/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!response.ok) {
    throw new Error("The assistant could not process that message. Please try again.");
  }
  return response.json();
}

async function submitMessage(message) {
  addMessage(message, "user");
  setSending(true);
  statusElement.textContent = "Assistant is working...";
  addTypingIndicator();

  try {
    const result = await sendMessage(message);
    addMessage(result.response, "assistant");
    if (result.requires_confirmation && result.pending_ticket) {
      showTicketConfirmation(result.pending_ticket);
    }
    if (result.ticket_number) {
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

if (window.matchMedia("(max-width: 760px)").matches) {
  appShell.classList.add("sidebar-collapsed");
}

bootstrap().catch((error) => {
  statusElement.textContent = error.message;
});
