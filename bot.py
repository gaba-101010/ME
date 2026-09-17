import os
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# تثبيت الموديل المعتمد لحسابك
MODEL_NAME = "groq/compound-mini"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    if "history" not in context.user_data:
        context.user_data["history"] = []
        
    history = context.user_data["history"]
    
    messages = [
        {
            "role": "system", 
            "content": f"You are an AI assistant running strictly on '{MODEL_NAME}'. Answer clearly and concisely in Arabic."
        }
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    clean_key = GROQ_API_KEY.strip() if GROQ_API_KEY else ""
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.6
    }
    
    reply = None
    last_error_details = ""
    max_retries = 3

    for attempt in range(max_retries):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                reply = res.json()['choices'][0]['message']['content']
                break
            else:
                try:
                    err_data = res.json()
                    err_msg = err_data.get("error", {}).get("message", res.text[:150])
                except Exception:
                    err_msg = res.text[:150]
                
                last_error_details = f"كود ({res.status_code}): {err_msg}"
                
                # إذا تجاوزت حد الدقيقة (429)، ينظر في وقت الانتظار المطلوب تلقائياً
                if res.status_code == 429:
                    time.sleep(5 * (attempt + 1))
                else:
                    time.sleep(1)
        except Exception as e:
            last_error_details = f"استثناء شبكة: {e}"
            time.sleep(1)

    if reply:
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        # تقليل السجل لآخر 6 عناصر لمنع تضخم التوكنات في الأسئلة الطويلة
        context.user_data["history"] = history[-6:]
    else:
        reply = f"⚠️ تعذر الاتصال بـ Groq:\n{last_error_details}"

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=1, stop_signals=None)
