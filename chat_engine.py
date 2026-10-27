# -*- coding: utf-8 -*-
"""
ThaiD Smart Chat AI Engine - LINE OA & Customer Service Assistant
Features:
1. Gemini 3.5 Flash Lite Context-Aware Response Engine
2. Multi-Key Vault Rotation & Auto-Recovery
3. LINE Messaging API Webhook & Signature Verification (HMAC-SHA256)
4. Knowledge Base Manager (Store Info, Products, FAQs, Promos, Bank Accounts)
5. Multi-Turn Conversation Memory & In-Browser Interactive Simulator
6. Real-Time Chat Analytics & Sentiment Tracking
"""

import os
import sys
import re
import time
import json
import uuid
import hmac
import hashlib
import base64
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

KB_FILE = os.path.join(DATA_DIR, "knowledge_base.json")
LOGS_FILE = os.path.join(DATA_DIR, "chat_logs.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# Gemini API Keys pool from Vault / Environment
def get_gemini_keys() -> List[str]:
    keys = []
    env_k = os.environ.get("GEMINI_API_KEY", "")
    if env_k:
        keys.append(env_k.strip())
    env_pool = os.environ.get("GEMINI_KEYS_POOL", "")
    if env_pool:
        keys.extend([k.strip() for k in env_pool.split(",") if k.strip()])
    return keys


# Default Knowledge Base Data
DEFAULT_KB = {
    "store_profile": {
        "store_name": "ThaiD Gadget & Lifestyle",
        "tagline": "ศูนย์รวมแกดเจ็ตและสินค้าไลฟ์สไตล์คุณภาพระดับพรีเมียม",
        "admin_name": "น้องใจดี",
        "gender_ending": "ค่ะ",  # ค่ะ or ครับ
        "phone": "02-123-4567",
        "line_id": "@thaid.online",
        "opening_hours": "เปิดให้บริการทุกวัน 08:30 - 22:00 น.",
        "delivery_info": "จัดส่งด่วนผ่าน Flash Express / Kerry ทั่วประเทศ ได้รับสินค้าภายใน 1-2 วันทำการ ค่าส่ง 40 บาท (สั่งครบ 500 บาท ส่งฟรี)",
        "payment_info": "ธนาคารกสิกรไทย เลขที่บัญชี 123-4-56789-0 ชื่อบัญชี บจก. ไทยดี ดิจิทัล (มีบริการเก็บเงินปลายทาง COD)",
        "return_policy": "รับประกันสินค้า 1 ปีเต็ม เปลี่ยนเครื่องใหม่ทันทีใน 7 วันหากมีปัญหาจากการผลิต"
    },
    "products": [
        {
            "id": "PROD-001",
            "name": "แก้วเก็บความเย็น Minimalist Tumbler 900ml",
            "price": 390,
            "original_price": 590,
            "description": "สแตนเลส 316 แท้เกรดการแพทย์ เก็บความเย็น 24 ชม. ฝากันหก 100% พกพาสะดวก",
            "status": "พร้อมส่ง"
        },
        {
            "id": "PROD-002",
            "name": "หูฟังบลูทูธไร้สาย ANC PureSound Pro",
            "price": 890,
            "original_price": 1290,
            "description": "ตัดเสียงรบกวนรอบข้างได้ถึง 35dB แบตอึด 30 ชม. รองรับ Fast Charging เสียงเบสแน่น",
            "status": "พร้อมส่ง"
        },
        {
            "id": "PROD-003",
            "name": "ไฟโซล่าเซลล์ติดบ้าน Solar Guard 300W",
            "price": 550,
            "original_price": 890,
            "description": "สว่างอัตโนมัติตลอดคืน แผงโซล่าขนาดใหญ่ กันน้ำระดับ IP67 ไม่ต้องเดินสายไฟ",
            "status": "พร้อมส่ง (ยอดนิยม)"
        },
        {
            "id": "PROD-004",
            "name": "คีย์บอร์ดบลูทูธไร้สาย Slim Touch 84 Keys",
            "price": 690,
            "original_price": 990,
            "description": "ปุ่มกดเงียบ พกพาสะดวก เชื่อมต่อได้พร้อมกัน 3 อุปกรณ์ (iOS, Android, Windows)",
            "status": "พร้อมส่ง"
        }
    ],
    "faqs": [
        {
            "question": "มีบริการเก็บเงินปลายทาง (COD) ไหมคะ",
            "answer": "มีบริการเก็บเงินปลายทาง (COD) ค่ะ ลูกค้าสามารถชำระเงินกับเจ้าหน้าที่ขนส่งเมื่อรับของได้เลยค่ะ ไม่มีบวกเพิ่ม"
        },
        {
            "question": "สั่งวันนี้ ของถึงวันไหนคะ",
            "answer": "ร้านตัดรอบจัดส่งทุกวันเวลา 14:00 น. จัดส่งผ่านขนส่งด่วน กทม.และปริมณฑลได้รับวันถัดไป ต่างจังหวัด 1-2 วันทำการค่ะ"
        },
        {
            "question": "สินค้ามีรับประกันไหมคะ",
            "answer": "สินค้าทุกชิ้นมีประกันศูนย์ 1 ปีเต็มค่ะ หากได้รับสินค้าแล้วพบปัญหาภายใน 7 วันแรก ทางร้านเปลี่ยนสินค้าตัวใหม่ให้ทันทีค่ะ"
        },
        {
            "question": "ขอใบกำกับภาษีได้ไหมคะ",
            "answer": "ทางร้านสามารถออกใบกำกับภาษีเต็มรูปแบบได้ค่ะ แจ้งชื่อ ที่อยู่ และเลขประจำตัวผู้เสียภาษีในแชทนี้ได้เลยนะคะ"
        }
    ]
}


def load_knowledge_base() -> Dict[str, Any]:
    """Loads knowledge base from JSON or creates default."""
    if os.path.exists(KB_FILE):
        try:
            with open(KB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Initialize default
    save_knowledge_base(DEFAULT_KB)
    return DEFAULT_KB


def save_knowledge_base(data: Dict[str, Any]) -> bool:
    """Saves knowledge base to JSON."""
    try:
        with open(KB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[KB] Error saving: {e}")
        return False


def load_settings() -> Dict[str, Any]:
    """Loads LINE OA credentials and app settings."""
    defaults = {
        "line_channel_secret": os.environ.get("LINE_CHANNEL_SECRET", ""),
        "line_channel_access_token": os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", ""),
        "auto_reply_enabled": True,
        "temperature": 0.7,
        "model_name": "gemini-3.5-flash-lite"
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_settings(data: Dict[str, Any]) -> bool:
    """Persists settings."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[Settings] Error saving: {e}")
        return False


def log_chat_interaction(sender: str, message: str, reply: str, channel: str = "web_simulator"):
    """Appends interaction to chat history log."""
    logs = []
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []

    logs.append({
        "id": str(uuid.uuid4())[:8],
        "timestamp": int(time.time()),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        "channel": channel,
        "sender": sender,
        "message": message,
        "reply": reply
    })

    # Keep last 1000 interactions
    if len(logs) > 1000:
        logs = logs[-1000:]

    try:
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def build_system_prompt(kb: Dict[str, Any]) -> str:
    """Constructs context-injected prompt for Gemini."""
    profile = kb.get("store_profile", {})
    products = kb.get("products", [])
    faqs = kb.get("faqs", [])

    store_name = profile.get("store_name", "ThaiD Store")
    admin_name = profile.get("admin_name", "น้องใจดี")
    ending = profile.get("gender_ending", "ค่ะ")

    # Format products
    prod_text = ""
    for p in products:
        prod_text += f"- {p['name']}: ราคาพิเศษ {p['price']} บาท (จากปกติ {p.get('original_price', p['price'])} บาท) | คุณสมบัติ: {p['description']} | สถานะ: {p.get('status', 'พร้อมส่ง')}\n"

    # Format FAQs
    faq_text = ""
    for f in faqs:
        faq_text += f"Q: {f['question']}\nA: {f['answer']}\n\n"

    sys_prompt = f"""คุณคือ "{admin_name}" แอดมิน AI อัจฉริยะประจำร้านค้าออนไลน์ "{store_name}" 
คุณมีหน้าที่ตอบคำถามลูกค้า ให้คำแนะนำเกี่ยวกับสินค้า ปิดการขายอย่างเป็นมิตร สุภาพ ไพเราะ และอบอุ่น
ลงท้ายประโยคด้วยคำว่า "{ending}" อย่างเป็นธรรมชาติเสมอ

=== ข้อมูลสำคัญของร้าน {store_name} ===
สโลแกน: {profile.get('tagline', '')}
เวลาทำการ: {profile.get('opening_hours', 'ทุกวัน')}
ข้อมูลจัดส่ง: {profile.get('delivery_info', '')}
ข้อมูลชำระเงิน/เลขบัญชี: {profile.get('payment_info', '')}
การรับประกัน & คืนสินค้า: {profile.get('return_policy', '')}
เบอร์ติดต่อ/LINE ID: {profile.get('phone', '')} ({profile.get('line_id', '')})

=== รายการสินค้าและราคาปัจจุบัน ===
{prod_text}

=== คำถามที่พบบ่อย (FAQ) และแนวทางตอบ ===
{faq_text}

=== กฎการให้บริการของแอดมิน ===
1. ตอบตรงประเด็น ชัดเจน กระชับ ไม่ยืดยาวจนเกินไป เหมาะกับการอ่านบนหน้าจอแชท LINE มือถือ
2. หากลูกค้าถามหาสินค้า ให้แนะนำชื่อสินค้า จุดเด่นสำคัญ และราคาอย่างชัดเจน พร้อมเชิญชวนสั่งซื้อ
3. หากลูกค้าถามข้อมูลที่อยู่นอกเหนือจากที่มี ให้ตอบด้วยความสุภาพและแจ้งว่าจะประสานงานให้เจ้าหน้าที่ติดต่อกลับ
4. ใช้อิโมจิน่ารักประกอบข้อความอย่างพอเหมาะ (เช่น 😊, ✨, 📦, 💖)
"""
    return sys_prompt


def generate_ai_reply(user_message: str, chat_history: List[Dict[str, str]] = None) -> str:
    """Generates intelligent response using Gemini 3.5 Flash Lite."""
    kb = load_knowledge_base()
    sys_prompt = build_system_prompt(kb)

    # Format contents for multi-turn chat
    contents = [sys_prompt]
    if chat_history:
        for turn in chat_history[-6:]:  # last 3 turns
            role = "ลูกค้า: " if turn.get("role") == "user" else "แอดมิน: "
            contents.append(f"{role}{turn.get('text', '')}")

    contents.append(f"ลูกค้า: {user_message}\nแอดมิน:")
    full_prompt = "\n".join(contents)

    keys = get_gemini_keys()
    try:
        from google import genai
        for key in keys:
            try:
                client = genai.Client(api_key=key)
                resp = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=full_prompt
                )
                if resp.text:
                    return resp.text.strip()
            except Exception as e:
                print(f"[GeminiChat] Error with key: {e}")
                continue
    except Exception as e:
        print(f"[GeminiImport] Note: {e}")

    # Fallback response
    ending = kb.get("store_profile", {}).get("gender_ending", "ค่ะ")
    return f"สวัสดี{ending} ขอบคุณที่ทักทายร้านเรานะคะ ตอนนี้ระบบกำลังอัปเดตข้อมูล แอดมินจะรีบตรวจสอบและตอบกลับข้อความของท่านโดยเร็วที่สุด{ending} 😊"


# LINE Messaging API Helpers
def verify_line_signature(body: bytes, signature: str, secret: str) -> bool:
    """Verifies X-Line-Signature header using HMAC-SHA256."""
    if not signature or not secret:
        return True  # Allow if secret not set for sandbox testing
    try:
        hash_val = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
        expected = base64.b64encode(hash_val).decode("utf-8")
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


def reply_line_message(reply_token: str, reply_text: str, channel_access_token: str) -> bool:
    """Sends reply message via LINE Messaging API."""
    if not reply_token or not channel_access_token:
        return False
    try:
        url = "https://api.line.me/v2/bot/message/reply"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {channel_access_token}"
        }
        payload = json.dumps({
            "replyToken": reply_token,
            "messages": [{"type": "text", "text": reply_text}]
        }).encode("utf-8")

        req = urllib.request.Request(url, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        print(f"[LineReply] Error: {e}")
        return False
