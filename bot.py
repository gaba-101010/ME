import os
import time
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

# جلب المفاتيح من بيئة التشغيل
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") or os.environ.get("GROQ_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# استخدام النموذج المعتمد والشغال عندك
MODEL_NAME = "groq/compound-mini"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    chat_id = update.message.chat_id
    
    # إظهار حالة "جاري الكتابة"
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")
    
    # تهيئة الذاكرة المؤقتة
    if "history" not in context.user_data:
        context.user_data["history"] = []
        
    history = context.user_data["history"]
    
    # إعداد الذاكرة والسياق
    messages = [
        {
            "role": "system", 
            "content": "You are a helpful AI assistant. Answer clearly and fully in Arabic."
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

    # محاولات إعادة الاتصال مع انتظار ذكي لامتصاص ضغط الدقيقة
    for attempt in range(max_retries):
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                reply = res.json()['choices'][0]['message']['content']
                break
            else:
                try:
                    err_data = res.json()
                    err_msg = err_data.get("error", {}).get("message", res.text[:120])
                except Exception:
                    err_msg = res.text[:120]
                
                last_error_details = f"كود الاستجابة ({res.status_code}): {err_msg}"
                
                # إذا كان السبب تجاوز حد الطلبات في الدقيقة (429 Rate Limit) ننتظر لتفريغ الضغط
                if res.status_code == 429:
                    time.sleep(4 * (attempt + 1)) # انتظار 4 ثم 8 ثم 12 ثانية
                else:
                    time.sleep(1)
        except Exception as e:
            last_error_details = f"استثناء شبكة: {e}"
            time.sleep(1)

    if reply:
        # حفظ آخر 4 محادثات
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})
        context.user_data["history"] = history[-8:]
    else:
        # إظهار السبب الحقيقي مباشرة بدون رسائل مضللة
        reply = f"⚠️ تعذر الاتصال بـ Groq:\n{last_error_details}"

    await update.message.reply_text(reply)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(poll_interval=1, stop_signals=None)
