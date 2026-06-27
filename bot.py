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

# 🔑 التوكن ومعرف المسؤول الخاص بك
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 945253440  

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

# 🌐 دالة سحب تيك توك 
async def fetch_tiktok_data(url):
    api_url = "https://tikwm.com"
    data = {"url": url, "hd": 1}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(api_url, data=data) as response:
                if response.status == 200:
                    res_json = await response.json()
                    if res_json.get("code") == 0:
                        return res_json.get("data")
        except Exception as e:
            print(f"TikTok API Error: {e}")
    return None

# 👻 دالة سحب سناب شات (تتعرف على الفيديو والصور للمنصة والقصص العامة)
async def fetch_snapchat_data(url):
    api_url = f"https://sandaww.com{url}" 
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                if response.status == 200:
                    res_json = await response.json()
                    if res_json.get("success"):
                        return res_json.get("data")
        except Exception as e:
            print(f"Snapchat API Error: {e}")
    return None

async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    register_user(user_id)
    
    welcome_text = (
        "👋 أهلاً بك في RzaVideoBot\n\n"
        "📥 أرسل رابط الفيديو - صور من TikTok، وسأقوم بمعالجته فوراً.\n\n"
        "⚡ سريع • سهل • مجاني"
    )
    welcome_msg = await update.message.reply_text(welcome_text)
    asyncio.create_task(delete_message_after_delay(context, chat_id, welcome_msg.message_id))
    asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_welcome_message(update, context)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_ID:
        total_users = get_users_count()
        await update.message.reply_text(f"📊 إحصائيات البوت الكلية:\n👥 عدد المستخدمين المسجلين: {total_users}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    url = update.message.text
    
    register_user(user_id)
    
    # 🚨 التحقق من روابط سناب شات وحظرها عن العامة والسماح لك فقط
    is_snapchat = "snapchat.com" in url
    if is_snapchat and user_id != ADMIN_ID:
        fail_msg = await update.message.reply_text("❌ عذراً، ميزة تحميل مقاطع سناب شات غير مدعومة حالياً للعامة.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=5))
        return

    # الفلترة الصحيحة لروابط التيك توك والمنصات الأخرى
    if not is_snapchat and "tiktok.com" not in url and "http" not in url:
        await send_welcome_message(update, context)
        return

    status_message = await update.message.reply_text("⏳ جاري سحب المحتوى ومعالجته، يرجى الانتظار...")

    # 👻 معالجة منصة سناب شات (خاصة بك فقط)
    if is_snapchat:
        snap_data = await fetch_snapchat_data(url)
        if not snap_data:
            fail_msg = await update.message.reply_text("❌ فشل سحب ميديا سناب شات. تأكد أن الحساب عام والقصة ليست خاصة.")
            asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
            try: await status_message.delete()
            except Exception: pass
            return

        media_url = snap_data.get("url")
        media_type = snap_data.get("type") 

        try:
            if media_type == "image":
                sent_media = await update.message.reply_photo(photo=media_url, caption="✅ تم سحب صورة سناب شات بنجاح.")
                asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
            else:
                sent_media = await update.message.reply_video(video=media_url, caption="✅ تم سحب فيديو سناب شات بنجاح.")
                asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
        except Exception as e:
            print(f"Snap Send Error: {e}")
            fail_msg = await update.message.reply_text("❌ حدث خطأ أثناء إرسال ميديا سناب شات.")
            asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
        finally:
            try: await status_message.delete()
            except Exception: pass
            asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=0))
            return

    # 🔗 معالجة منصة تيك توك للجميع
    tiktok_data = await fetch_tiktok_data(url)

    if not tiktok_data:
        fail_msg = await update.message.reply_text("❌ فشل في سحب المحتوى، تأكد من أن الحساب ليس خاصاً أو جرب رابط آخر.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
        try: await status_message.delete()
        except Exception: pass
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=0))
        return

    try:
        if "images" in tiktok_data and tiktok_data["images"]:
            images_list = tiktok_data["images"]
            media_group = [InputMediaPhoto(media=img_url) for img_url in images_list[:10]]
            
            sent_media = await update.message.reply_media_group(media=media_group)
            thanks_msg = await update.message.reply_text("✅ تم تجهيز الصور بنجاح.")
            
            for msg in sent_media:
                asyncio.create_task(delete_message_after_delay(context, chat_id, msg.message_id))
            asyncio.create_task(delete_message_after_delay(context, chat_id, thanks_msg.message_id))
        else:
            video_url = tiktok_data.get("hdplay") or tiktok_data.get("play")
            if video_url:
                sent_media = await update.message.reply_video(video=video_url, caption="✅ تم تجهيز الفيديو بنجاح.")
                asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
            else:
                fail_msg = await update.message.reply_text("❌ لم نتمكن من العثور على ملف الفيديو في الرابط.")
                asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
    except Exception as e:
        print(f"TikTok Send Error: {e}")
        fail_msg = await update.message.reply_text("❌ حدث خطأ أثناء إرسال الميديا.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
    finally:
        try: await status_message.delete()
        except Exception: pass
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=0))

def main():
    if not BOT_TOKEN:
        print("Error: BOT_TOKEN is missing!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", stats))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("RzaVideoBot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
