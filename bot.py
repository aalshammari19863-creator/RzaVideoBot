import os
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")

# دالة مساعدة لحذف الرسائل تلقائياً بعد 45 ثانية لضمان الخصوصية وتنظيف الشات
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 45):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

# دالة لتنزيل الفيديو أو الصور باستخدام yt-dlp
def download_tiktok(url):
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        if 'entries' in info:
            files = []
            for entry in info['entries']:
                file_path = ydl.prepare_filename(entry)
                if os.path.exists(file_path):
                    files.append(file_path)
            return "images", files
        else:
            file_path = ydl.prepare_filename(info)
            if not os.path.exists(file_path):
                base, _ = os.path.splitext(file_path)
                for ext in ['mp4', 'mkv', 'webm', 'jpg', 'png']:
                    if os.path.exists(f"{base}.{ext}"):
                        file_path = f"{base}.{ext}"
                        break
            return "video", file_path

# دالة موحدة لعرض رسالة الترحيب الرسمية المطلوبة
async def send_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    welcome_text = (
        "👋 أهلاً بك في RzaVideoBot\n\n"
        "شكراً لاستخدامك البوت، يسعدنا وجودك معنا 🤍\n\n"
        "📥 أرسل رابط الفيديو - صور من TikTok أو أي منصة مدعومة، وسأقوم بمعالجته وإرسال الفيديو لك بأفضل جودة ممكنة.\n\n"
        "⚡ سريع • سهل • مجاني\n\n"
        "نتمنى لك تجربة ممتعة، ولا تتردد في مشاركة البوت مع أصدقائك.\n\n"
        "— فريق Rza"
    )
    
    welcome_msg = await update.message.reply_text(welcome_text)
    
    # حذف رسالة الترحيب ورسالة المستخدم بعد 45 ثانية
    asyncio.create_task(delete_message_after_delay(context, chat_id, welcome_msg.message_id))
    asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id))

# أمر البدء /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_welcome_message(update, context)

# معالج النصوص والروابط المرسلة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    url = update.message.text
    
    # التحقق من الرابط، وإذا كانت الرسالة غير مفهومة يتم تحويلها تلقائياً لرسالة الترحيب
    if "tiktok.com" not in url and "http" not in url:
        await send_welcome_message(update, context)
        return

    status_message = await update.message.reply_text("⏳ جاري سحب المحتوى ومعالجته، يرجى الانتظار...")

    try:
        loop = asyncio.get_event_loop()
        media_type, file_data = await loop.run_in_executor(None, download_tiktok, url)

        # رسالة الشكر الرسمية المطلوبة بعد تحميل الفيديو أو الصور
        thank_you_text = (
            "✅ تم تجهيز الفيديو بنجاح.\n\n"
            "شكراً لاستخدامك RzaVideoBot 🤍\n\n"
            "نتمنى أن تكون الخدمة قد نالت إعجابك، ويسعدنا دعمك بمشاركة البوت مع أصدقائك.\n\n"
            "نراك قريباً."
        )

        if media_type == "video" and os.path.exists(file_data):
            with open(file_data, 'rb') as video:
                sent_media = await update.message.reply_video(video=video, caption=thank_you_text)
            os.remove(file_data)
            asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
            
        elif media_type == "images" and file_data:
            for file_path in file_data:
                with open(file_path, 'rb') as photo:
                    sent_media = await update.message.reply_photo(photo=photo)
                os.remove(file_path)
                asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
            
            thanks_msg = await update.message.reply_text(thank_you_text)
            asyncio.create_task(delete_message_after_delay(context, chat_id, thanks_msg.message_id))
        else:
            fail_msg = await update.message.reply_text("❌ فشل في تحميل المحتوى، يرجى تجربة رابط آخر.")
            asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))

    except Exception as e:
        print(f"Error: {e}")
        fail_msg = await update.message.reply_text("❌ حدث خطأ أثناء معالجة الرابط، تأكد من صحته.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))

    finally:
        # حذف رسالة الانتظار فوراً، وحذف رسالة المستخدم الأصلية التي بها الرابط
        try:
            await status_message.delete()
        except Exception:
            pass
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=0))

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Started")
    app.run_polling()

if __name__ == "__main__":
    main()
