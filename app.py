# -*- coding: utf-8 -*-
"""
ThaiD Smart Chat AI Studio - Web Application Server
Production FastAPI Backend for https://chat.thaid.online
AI Customer Service Assistant with LINE OA Webhook & Knowledge Base
"""

import os
import sys
import time
import json
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Request, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

import chat_engine as ce

app = FastAPI(
    title="ThaiD Smart Chat AI Studio",
    description="Intelligent AI Customer Service & LINE OA Assistant",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SimulateChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None


class SaveKbRequest(BaseModel):
    store_profile: Dict[str, Any]
    products: List[Dict[str, Any]]
    faqs: List[Dict[str, Any]]


class SaveSettingsRequest(BaseModel):
    line_channel_secret: Optional[str] = ""
    line_channel_access_token: Optional[str] = ""
    auto_reply_enabled: bool = True


@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "ThaiD Smart Chat AI Studio Live"}


@app.get("/api/status")
def get_system_status():
    """Health check, KB stats, and connection status."""
    kb = ce.load_knowledge_base()
    settings = ce.load_settings()
    has_line = bool(settings.get("line_channel_access_token") and settings.get("line_channel_secret"))

    return {
        "ok": True,
        "service": "ThaiD Smart Chat AI Studio",
        "domain": "chat.thaid.online",
        "status": "online",
        "ai_model": "Gemini 3.5 Flash Lite",
        "store_name": kb.get("store_profile", {}).get("store_name", "ThaiD Store"),
        "total_products": len(kb.get("products", [])),
        "total_faqs": len(kb.get("faqs", [])),
        "line_oa_connected": has_line,
        "webhook_url": "https://chat.thaid.online/webhook"
    }


@app.get("/api/kb")
def api_get_kb():
    """Returns current knowledge base."""
    return {"ok": True, "kb": ce.load_knowledge_base()}


@app.post("/api/kb/save")
def api_save_kb(req: SaveKbRequest):
    """Saves updated knowledge base."""
    data = {
        "store_profile": req.store_profile,
        "products": req.products,
        "faqs": req.faqs
    }
    if ce.save_knowledge_base(data):
        return {"ok": True, "message": "Knowledge base updated successfully"}
    raise HTTPException(status_code=500, detail="Failed to save knowledge base")


@app.get("/api/settings")
def api_get_settings():
    """Returns current settings (masking access token)."""
    s = ce.load_settings()
    token = s.get("line_channel_access_token", "")
    masked_token = (token[:10] + "..." + token[-6:]) if len(token) > 20 else token
    return {
        "ok": True,
        "settings": {
            "line_channel_secret": s.get("line_channel_secret", ""),
            "line_channel_access_token_masked": masked_token,
            "has_token": bool(token),
            "auto_reply_enabled": s.get("auto_reply_enabled", True)
        }
    }


@app.post("/api/settings/save")
def api_save_settings(req: SaveSettingsRequest):
    """Updates LINE OA settings."""
    current = ce.load_settings()
    if req.line_channel_secret is not None:
        current["line_channel_secret"] = req.line_channel_secret
    if req.line_channel_access_token:
        current["line_channel_access_token"] = req.line_channel_access_token
    current["auto_reply_enabled"] = req.auto_reply_enabled

    if ce.save_settings(current):
        return {"ok": True, "message": "Settings saved successfully"}
    raise HTTPException(status_code=500, detail="Failed to save settings")


@app.post("/api/chat/simulate")
def api_simulate_chat(req: SimulateChatRequest):
    """
    In-Browser Web Simulator:
    Chat with the AI assistant in real-time without needing a LINE OA account.
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    t0 = time.time()
    reply = ce.generate_ai_reply(req.message, req.history)
    elapsed = round(time.time() - t0, 2)

    # Log interaction
    ce.log_chat_interaction(
        sender="Simulator_User",
        message=req.message,
        reply=reply,
        channel="web_simulator"
    )

    return {
        "ok": True,
        "reply": reply,
        "elapsed": elapsed
    }


@app.get("/api/chat/logs")
def api_get_chat_logs(limit: int = 50):
    """Returns recent chat interaction history."""
    logs = []
    if os.path.exists(ce.LOGS_FILE):
        try:
            with open(ce.LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    
    return {
        "ok": True,
        "total_messages": len(logs),
        "logs": list(reversed(logs[-limit:]))
    }


@app.post("/webhook")
async def line_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Official LINE Messaging API Webhook:
    Receives events from LINE, processes messages, and replies via Gemini AI.
    """
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    settings = ce.load_settings()
    secret = settings.get("line_channel_secret", "")
    token = settings.get("line_channel_access_token", "")

    # Verify signature if secret configured
    if secret and not ce.verify_line_signature(body, signature, secret):
        raise HTTPException(status_code=400, detail="Invalid signature")

    try:
        data = json.loads(body.decode("utf-8"))
        events = data.get("events", [])

        for ev in events:
            ev_type = ev.get("type")
            if ev_type == "message":
                msg = ev.get("message", {})
                if msg.get("type") == "text":
                    user_text = msg.get("text", "")
                    reply_token = ev.get("replyToken")
                    user_id = ev.get("source", {}).get("userId", "LINE_User")

                    # Generate reply via Gemini
                    ai_reply = ce.generate_ai_reply(user_text)

                    # Send reply via LINE API
                    if token and reply_token:
                        background_tasks.add_task(ce.reply_line_message, reply_token, ai_reply, token)

                    # Log interaction
                    ce.log_chat_interaction(
                        sender=user_id,
                        message=user_text,
                        reply=ai_reply,
                        channel="line_oa"
                    )

        return Response(content="OK", status_code=200)
    except Exception as e:
        print(f"[Webhook] Error processing event: {e}")
        return Response(content="OK", status_code=200)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8094, reload=True)
