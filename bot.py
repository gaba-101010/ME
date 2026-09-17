import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

def get_working_model():
    """فحص واختيار الموديل الشغال في حسابك تلقائياً"""
    url = "https://api.groq.com/openai/v1/models"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            models = [m["id"] for m in res.json().get("data", [])]
            for preferred in ["llama3-8b-8192", "mixtral-8x7b-32768", "gemma2-9b-it", "llama-3.3-70b-versatile"]:
                if preferred in models:
                    return preferred
            if models:
                return models[0]
    except Exception:
        pass
    return "llama3-8b-8192"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    selected_model = get_working_model()
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": selected_model,
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
            reply = f"⚠️ خطأ Groq (كود {res.status_code}): {res.text[:150]}"
    except Exception as e:
        reply = f"❌ خطأ تقني: {e}"

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=1, stop_signals=None)
