import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
SNAPCHAT_URL = "https://snapchat.com/t/8vTBUxxn"

# دالة مساعدة لحذف الرسائل تلقائياً بعد وقت محدد
async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 45):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass # يتجاهل الخطأ إذا قام المستخدم بحذف الرسالة بنفسه أولاً

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

# أمر البدء (تعديل لطلب زيارة السناب شات)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    
    keyboard = [
        [InlineKeyboardButton("👻 زيارة حساب سناب شات", url=SNAPCHAT_URL)],
        [InlineKeyboardButton("✅ تم، أنا جاهز الآن!", callback_data="verified")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_msg = await update.message.reply_text(
        "👋 أهلاً بك في RzaVideoBot\n\n"
        "يسعدنا جداً استخدامك للبوت! قبل البدء، يرجى التكرم بزيارة حسابنا على سناب شات ودعمنا بالاشتراك لمتابعة كل جديد ✨\n\n"
        "بعد الزيارة، يمكنك إرسال أي رابط تيك توك مباشرة للتحميل بدون علامة مائية.",
        reply_markup=reply_markup
    )
    
    # تشغيل مؤقت لحذف رسالة الترحيب بعد 45 ثانية
    asyncio.create_task(delete_message_after_delay(context, chat_id, welcome_msg.message_id))

# معالج الروابط المرسلة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    url = update.message.text
    
    if "tiktok.com" not in url:
        err_msg = await update.message.reply_text("❌ عذراً، هذا الرابط لا يبدو كرابط تيك توك صحيح.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, err_msg.message_id))
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id))
        return

    status_message = await update.message.reply_text("⏳ جاري سحب المحتوى ومعالجته، يرجى الانتظار...")

    try:
        loop = asyncio.get_event_loop()
        media_type, file_data = await loop.run_in_executor(None, download_tiktok, url)

        # رسالة شكر راقية تظهر مع الميديا
        thank_you_text = "🤍 شكراً لك على ثقتك بـ RzaVideoBot.\n\nتم تحميل طلبك بنجاح وبأعلى جودة بدون حقوق. يسعدنا دائماً خدمتك! ✨"

        if media_type == "video" and os.path.exists(file_data):
            with open(file_data, 'rb') as video:
                sent_media = await update.message.reply_video(video=video, caption=thank_you_text)
            os.remove(file_data)
            # حذف الميديا ورسالة المستخدم بعد 45 ثانية
            asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
            
        elif media_type == "images" and file_data:
            for file_path in file_data:
                with open(file_path, 'rb') as photo:
                    sent_media = await update.message.reply_photo(photo=photo)
                os.remove(file_path)
                asyncio.create_task(delete_message_after_delay(context, chat_id, sent_media.message_id))
            
            # إرسال رسالة الشكر منفصلة للصور
            thanks_msg = await update.message.reply_text(thank_you_text)
            asyncio.create_task(delete_message_after_delay(context, chat_id, thanks_msg.message_id))
        else:
            fail_msg = await update.message.reply_text("❌ فشل في تحميل المحتوى، يرجى تجربة رابط آخر.")
            asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))

    except Exception as e:
        print(f"Error: {e}")
        fail_msg = await update.message.reply_text("❌ حدث خطأ غير متوقع أثناء معالجة الرابط.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))

    finally:
        # حذف رسالة الحالة (جاري التحميل) ورسالة المستخدم المرسلة الأصلية
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
