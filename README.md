# AI Operations Assistant

A Python/FastAPI IT support agent. LangGraph lets the model select the appropriate action: search internal support documents, look up an existing ticket, or create a new ticket. Internal document embeddings are persisted in a local FAISS index.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY` in `.env`, then add PDF, DOCX, TXT, or Markdown documents to `data/knowledge_base/`.

```powershell
python -m scripts.ingest_knowledge_base
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to use the API.

## Local test sequence

Run the following commands from the project root after adding an `OPENAI_API_KEY` to `.env`:

```powershell
python -m scripts.ingest_knowledge_base
uvicorn app.main:app --reload
```

In a second terminal, create a conversation and retain the returned `conversation_id`:

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8000/conversations
```

Then send a knowledge-base question:

```powershell
$conversationId = "replace-with-conversation-id"
Invoke-RestMethod -Method Post "http://127.0.0.1:8000/conversations/$conversationId/messages" `
  -ContentType "application/json" `
  -Body '{"message":"My VPN shows Authentication failed. What should I do?"}'
```

For a ticket creation flow, send `My VPN is not working. Please create a ticket.` The assistant prepares a ticket draft first. Review the displayed title, description, category, priority, device, and error details, then select **Confirm and create ticket**. Only that explicit confirmation lets the agent call the ticket-creation tool.

## Main endpoints

- `POST /conversations` creates a conversation.
- `POST /conversations/{conversation_id}/messages` sends a chat message to the agent.
- `GET /tickets` and `GET /tickets/{ticket_number}` inspect support tickets.
- `GET /knowledge/search?query=vpn` searches indexed documents directly.

## Agent flow

```text
User message -> LangGraph decision -> selected tool -> response
                                  |-> knowledge_search
                                  |-> ticket_lookup
                                  |-> ticket_creation
```
