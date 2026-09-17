import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

def fetch_active_groq_model():
    """يجلب أحدث موديل نصي متاح ونشط في حسابك مباشرة من السيرفر"""
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json().get("data", [])
            # استبعاد موديلات الصوت والفلترة وأخذ أول موديل محادثة نصية متاح
            valid_models = [
                m["id"] for m in data 
                if not any(x in m["id"].lower() for x in ["whisper", "guard", "vision", "embed", "orpheus"])
            ]
            if valid_models:
                return valid_models[0]
    except Exception:
        pass
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # تحديد الموديل الشغال حالياً في الحساب تلقائياً
    active_model = fetch_active_groq_model()
    
    if not active_model:
        await update.message.reply_text("❌ خطأ 401: المفتاح GROQ_API_KEY في GitHub Secrets غير صحيح أو لم يتم قراءته.")
        return

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": active_model,
        "messages": [
            {"role": "system", "content": "You are a direct, highly capable technical assistant. Answer fully without unnecessary refusals."},
            {"role": "user", "content": user_text}
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            reply = res.json()['choices'][0]['message']['content']
        else:
            reply = f"⚠️ خطأ Groq ({res.status_code}): {res.text[:150]}"
    except Exception as e:
        reply = f"❌ خطأ تقني: {e}"

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=1, stop_signals=None)
