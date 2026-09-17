import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# تثبيت الموديل الأساسي والمعتمد في Groq
MODEL_NAME = "llama-3.3-70b-versatile"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # تهيئة الذاكرة المؤقتة في جلسة المستخدم
    if "history" not in context.user_data:
        context.user_data["history"] = []
        
    history = context.user_data["history"]
    
    # تحديد النظام وإعلام البوت بموديله الصريح
    messages = [
        {
            "role": "system", 
            "content": f"You are a technical AI assistant running on the '{MODEL_NAME}' model via Groq. Use context from previous messages to deliver precise responses."
        }
    ]
    
    # دمج السجل السابق مع الرسالة الجديدة
    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.6
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            reply = res.json()['choices'][0]['message']['content']
            
            # حفظ السؤال والرد في الذاكرة
            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": reply})
            
            # الاحتفاظ بآخر 8 عناصر (أخر 4 أسئلة و4 ردود) لضمان الفهم والسياق
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
