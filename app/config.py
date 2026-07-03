"""
Central place for every environment variable the app needs.
Import from here everywhere else, never call os.environ directly in other files.
That way, if a variable is missing, the app fails immediately on startup with a
clear error, instead of failing mysteriously halfway through a WhatsApp reply.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

# --- WhatsApp Cloud API ---
WHATSAPP_TOKEN = require("WHATSAPP_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = require("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_VERIFY_TOKEN = require("WHATSAPP_VERIFY_TOKEN")
WHATSAPP_APP_SECRET = os.environ.get("WHATSAPP_APP_SECRET", "")
GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v23.0")

# --- Claude (Anthropic) ---
ANTHROPIC_API_KEY = require("ANTHROPIC_API_KEY")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")

# --- Voyage AI (embeddings) ---
VOYAGE_API_KEY = require("VOYAGE_API_KEY")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "voyage-4-lite")

# --- Qdrant (vector database) ---
QDRANT_URL = require("QDRANT_URL")
QDRANT_API_KEY = require("QDRANT_API_KEY")
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "knowledge_base")

# --- RAG behaviour ---
TOP_K = int(os.environ.get("TOP_K", "4"))
