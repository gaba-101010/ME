import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

def get_startup_model():
    """فحص واختيار الموديل المتاح في حسابك مرة واحدة فقط عند إقلاع البوت"""
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    
    preferred_models = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "gemma2-9b-it",
        "deepseek-r1-distill-llama-70b"
    ]
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            available = [m["id"] for m in res.json().get("data", [])]
            # 1. اختيار أول موديل مفضل موجود بحسابك
            for p in preferred_models:
                if p in available:
                    return p
            # 2. إذا لم يجد مفضل، يأخذ أول موديل محادثة نصية
            for m in available:
                if not any(bad in m.lower() for bad in ["whisper", "guard", "vision", "embed", "orpheus"]):
                    return m
    except Exception:
        pass
    
    return "llama-3.1-8b-instant"

# تحديد الموديل مرة واحدة فقط في الذاكرة عند بداية التشغيل
ACTIVE_MODEL = get_startup_model()
print(f"✅ تم اعتماد الموديل المتاح في حسابك بنجاح: {ACTIVE_MODEL}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # تهيئة الذاكرة التراكمية
    if "history" not in context.user_data:
        context.user_data["history"] = []
        
    history = context.user_data["history"]
    
    messages = [
        {
            "role": "system", 
            "content": f"You are a technical assistant powered by '{ACTIVE_MODEL}'. Answer directly and concisely."
        }
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": ACTIVE_MODEL,
        "messages": messages,
        "temperature": 0.6
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            reply = res.json()['choices'][0]['message']['content']
            
            # حفظ المحادثة ليتذكر آخر 4 أسئلة و4 أجوِبة (8 عناصر)
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply})
            context.user_data["history"] = history[-8:]
        else:
            reply = f"⚠️ خطأ Groq ({res.status_code}): {res.text[:150]}"
    except Exception as e:
        reply = f"❌ خطأ تقني: {e}"

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=1, stop_signals=None)
