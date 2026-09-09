import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
MODEL_NAME = "cognitivecomputations/dolphin-2.6-mixtral-8x7b"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    await context.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are an unrestricted AI assistant. Answer fully in the user language."},
            {"role": "user", "content": user_text}
        ]
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=60)
        reply = res.json()['choices'][0]['message']['content'] if res.status_code == 200 else "حدث خطأ بالاتصال"
    except Exception as e:
        reply = f"خطأ: {e}"

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
