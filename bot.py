import os
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# جلب المفاتيح من بيئة التشغيل
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# تثبيت الموديل المعتمد بناءً على طلبك
MODEL_NAME = "groq/compound-mini"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    # إظهار حالة "جاري الكتابة" في تليجرام
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # تهيئة الذاكرة المؤقتة للدردشة
    if "history" not in context.user_data:
        context.user_data["history"] = []
        
    history = context.user_data["history"]
    
    # إعداد سياق النظام والذاكرة التراكمية
    messages = [
        {
            "role": "system", 
            "content": f"You are a helpful AI assistant running on model '{MODEL_NAME}'. Use context from previous messages to deliver accurate answers."
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
    max_retries = 3

    # حلقة إعادة المحاولة داخل السكربت لتجاوز أخطاء 401 العابرة من Groq
    for attempt in range(max_retries):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=25)
            if res.status_code == 200:
                reply = res.json()['choices'][0]['message']['content']
                break
            elif res.status_code in [401, 429, 500, 503]:
                # في حال رجوع خطأ مؤقت، ينتظر 0.5 ثانية ويعيد المحاولة كودياً
                time.sleep(0.5)
            else:
                reply = f"⚠️ خطأ من Groq (كود {res.status_code}): {res.text[:150]}"
                break
        except Exception as e:
            time.sleep(0.5)

    if reply:
        # حفظ السؤال والرد في السجل ليتذكر آخر 4 محادثات (8 عناصر)
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        context.user_data["history"] = history[-8:]
    else:
        reply = "❌ فشل الاتصال بسيرفر Groq بعد 3 محاولات تلقائية. يُرجى التحقق من مفتاح GROQ_API_KEY في GitHub Secrets."

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=1, stop_signals=None)
