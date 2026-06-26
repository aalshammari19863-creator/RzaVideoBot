




import os
import asyncio
import aiohttp
import sqlite3
from telegram import Update, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# 🔑 التوكن ومعرف المسؤول
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 945253440  # ⚠️ استبدل هذا الرقم بـ ID حسابك على تليغرام لتتمكن من رؤية الإحصائيات

# 🗄️ إعداد قاعدة البيانات وتجهيزها عند إقلاع البوت
DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 📝 دالة لتسجيل المستخدمين الجدد في قاعدة البيانات
def register_user(user_id: int):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

# 📊 دالة لجلب العدد الإجمالي للمستخدمين
def get_users_count() -> int:
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"Database Error: {e}")
        return 0

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 45):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def fetch_tiktok_data(url):
    api_url = "https://www.tikwm.com/api/"
    data = {"url": url, "hd": 1}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(api_url, data=data) as response:
                if response.status == 200:
                    res_json = await response.json()
                    if res_json.get("code") == 0:
                        return res_json.get("data")
        except Exception as e:
            print(f"API Error: {e}")
    return None

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # حفظ المستخدم الجديد فوراً عند الضغط على /start
    register_user(user_id)
    
    welcome_text = (
        "👋 أهلاً بك في RzaVideoBot\n\n"
        "شكراً لاستخدامك البوت، يسعدنا وجودك معنا 🤍\n\n"
        "📥 أرسل رابط الفيديو - صور من TikTok أو أي منصة مدعومة، وسأقوم بمعالجته وإرسال الفيديو لك بأفضل جودة ممكنة.\n\n"
        "⚡ سريع • سهل • مجاني\n\n"
        "نتمنى لك تجربة ممتعة، ولا تتردد في مشاركة البوت مع أصدقائك.\n\n"
        "— فريق Rza"
    )
    welcome_msg = await update.message.reply_text(welcome_text)
    asyncio.create_task(delete_message_after_delay(context, chat_id, welcome_msg.message_id))
    asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_welcome_message(update, context)

# 📊 أمر خاص بالمسؤول فقط لمعرفة الإحصائيات الكلية
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        total_users = get_users_count()
        await update.message.reply_text(f"📊 إحصائيات البوت الكلية:\n👥 عدد المستخدمين المسجلين: {total_users}")
    else:
        # إذا حاول شخص آخر استخدام الأمر لن يظهر له شيء
        pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    url = update.message.text
    
    # حفظ المستخدم تلقائياً عند إرسال أي رسالة للبوت لضمان تسجيله
    register_user(user_id)
    
    if "tiktok.com" not in url and "http" not in url:
        await send_welcome_message(update, context)
        return

    status_message = await update.message.reply_text("⏳ جاري سحب المحتوى ومعالجته، يرجى الانتظار...")

    thank_you_text = (
        "✅ تم تجهيز الفيديو بنجاح.\n\n"
        "شكراً لاستخدامك RzaVideoBot 🤍\n\n"
        "نتمنى أن تكون الخدمة قد نالت إعجابك، ويسعدنا دعمك بمشاركة البوت مع أصدقائك.\n\n"
        "نراك قريباً."
    )
    
    thank_you_images_text = (
        "✅ تم تجهيز الصور بنجاح.\n\n"
        "شكراً لاستخدامك RzaVideoBot 🤍\n\n"
        "نتمنى أن تكون الخدمة قد نالت إعجابك، ويسعدنا دعمك بمشاركة البوت مع أصدقائك.\n\n"
        "نراك قريباً."
    )

    tiktok_data = await fetch_tiktok_data(url)

    if not tiktok_data:
        fail_msg = await update.message.reply_text("❌ فشل في سحب المحتوى، تأكد من أن الحساب ليس خاصاً أو جرب رابط آخر.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
        try:
            await status_message.delete()
        except Exception: pass
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=0))
        return

    try:
        if "images" in tiktok_data and tiktok_data["images"]:
            images_list = tiktok_data["images"]
            media_group = []
            for img_url in images_list[:10]:
                media_group.append(InputMediaPhoto(media=img_url))
            
            sent_media = await update.message.reply_media_group(media=media_group)
            thanks_msg = await update.message.reply_text(thank_you_images_text)
            
            for msg in sent_media:
                asyncio.create_task(delete_message_after_delay(context, chat_id, msg.message_id))
            asyncio.create_task(delete_message_after_delay(context, chat_id, thanks_msg.message_id))
        else:
            video_url = tiktok_data.get("hdplay") or tiktok_data.get("play")
            if video_url:
                sent_media = await update.message.reply_video(video=video_url, caption=thank_you_text)
                asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
            else:
                fail_msg = await update.message.reply_text("❌ لم نتمكن من العثور على ملف الفيديو في الرابط.")
                asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
    except Exception as e:
        print(f"Send Error: {e}")
        fail_msg = await update.message.reply_text("❌ حدث خطأ أثناء إرسال الميديا.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
    finally:
        try:
            await status_message.delete()
        except Exception: pass
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=0))

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", stats)) # أضفنا الأمر هنا
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("RzaVideoBot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
