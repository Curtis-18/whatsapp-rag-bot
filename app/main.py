"""
The FastAPI app. Three routes matter:

GET  /webhook          - Meta calls this ONCE, when you click "Verify and
                          Save" in the App Dashboard. Must echo back
                          hub.challenge, or the subscription is rejected.
POST /webhook          - Meta calls this every time a WhatsApp event
                          happens. We only act on actual incoming text
                          messages and ignore the rest.
GET  /admin/reingest    - You visit this in a browser after editing files in
                          knowledge_base/ and redeploying, to reload the
                          knowledge base into Qdrant without running any
                          script yourself.

On top of that, the app auto-loads the knowledge base the very first time
it boots (see `lifespan` below), so a brand new deployment isn't empty.

Run locally with: uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response

from app.config import WHATSAPP_VERIFY_TOKEN
from app.whatsapp import send_text_message, verify_signature
from app.rag import answer_question
from app.vectorstore import collection_exists
from scripts.ingest import main as run_ingest


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        if not collection_exists():
            print("No knowledge base in Qdrant yet, running first-time ingestion...")
            run_ingest()
        else:
            print("Knowledge base already loaded, skipping ingestion on startup. "
                  "Visit /admin/reingest to refresh it.")
    except Exception as e:
        # Never let a knowledge-base problem stop the bot from starting, the
        # webhook should still come up so WhatsApp verification doesn't fail.
        print(f"Startup ingestion check failed: {e}")
    yield


app = FastAPI(title="WhatsApp RAG Bot", lifespan=lifespan)


@app.get("/")
def health():
    return {"status": "running"}


@app.get("/admin/reingest")
def reingest(token: str = ""):
    """
    Visit https://your-app.onrender.com/admin/reingest?token=YOUR_VERIFY_TOKEN
    any time after editing knowledge_base/ and redeploying, to wipe and
    reload the knowledge base. Uses your WHATSAPP_VERIFY_TOKEN as the
    password so there's nothing extra to set up.
    """
    if token != WHATSAPP_VERIFY_TOKEN:
        return Response(status_code=403)
    try:
        result = run_ingest()
        return {"status": "ok", **result}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/webhook")
def verify_webhook(request: Request):
    params = request.query_params
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == WHATSAPP_VERIFY_TOKEN
    ):
        return Response(content=params.get("hub.challenge", ""), media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def receive_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")
    if not verify_signature(raw_body, signature):
        return Response(status_code=403)

    data = await request.json()

    try:
        change_value = data["entry"][0]["changes"][0]["value"]
        messages = change_value.get("messages")
        if not messages:
            # This is a status update (delivered/read), not a new message. Ignore it.
            return {"status": "ignored"}

        message = messages[0]
        sender = message["from"]

        if message.get("type") != "text":
            send_text_message(
                sender,
                "I can only read text messages right now, could you type your question?",
            )
            return {"status": "ok"}

        user_text = message["text"]["body"]
        reply = answer_question(user_text)
        send_text_message(sender, reply)

    except (KeyError, IndexError):
        # Payload didn't look like a message event we understand. Don't crash the webhook.
        pass

    return {"status": "ok"}
