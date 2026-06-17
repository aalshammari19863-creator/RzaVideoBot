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

# دالة لتنزيل الفيديو أو الصور باستخدام yt-dlp
def download_tiktok(url):
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s', # حفظ الملفات في مجلد downloads
        'quiet': True,
        'no_warnings': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        
        # إذا كان الرابط ألبوم صور
        if 'entries' in info:
            files = []
            for entry in info['entries']:
                file_path = ydl.prepare_filename(entry)
                if os.path.exists(file_path):
                    files.append(file_path)
            return "images", files
            
        # إذا كان الرابط فيديو واحد
        else:
            file_path = ydl.prepare_filename(info)
            # بعض الأحيان الامتداد يختلف عند التحميل الفعلي، نتأكد من وجود الملف
            if not os.path.exists(file_path):
                base, _ = os.path.splitext(file_path)
                for ext in ['mp4', 'mkv', 'webm', 'jpg', 'png']:
                    if os.path.exists(f"{base}.{ext}"):
                        file_path = f"{base}.{ext}"
                        break
            return "video", file_path

# أمر البدء
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في RzaVideoBot\n\n"
        "أرسل لي أي رابط تيك توك (فيديو أو ألبوم صور) وسأقوم بتحميله بدون علامة مائية فوراً!"
    )

# معالج الروابط المرسلة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    
    # التأكد أن الرابط يخص تيك توك
    if "tiktok.com" not in url:
        await update.message.reply_text("❌ عذراً، هذا الرابط لا يبدو كرابط تيك توك صحيح.")
        return

    status_message = await update.message.reply_text("⏳ جاري التحميل، يرجى الانتظار...")

    try:
        # تشغيل دالة التحميل في خلفية منفصلة حتى لا يتوقف البوت عن الاستجابة
        loop = asyncio.get_event_loop()
        media_type, file_data = await loop.run_in_executor(None, download_tiktok, url)

        if media_type == "video" and os.path.exists(file_data):
            # إرسال فيديو
            with open(file_data, 'rb') as video:
                await update.message.reply_video(video=video)
            os.remove(file_data) # حذف الملف بعد الإرسال لتوفير المساحة
            
        elif media_type == "images" and file_data:
            # إرسال ألبوم صور
            for file_path in file_data:
                with open(file_path, 'rb') as photo:
                    await update.message.reply_photo(photo=photo)
                os.remove(file_path) # حذف الصور بعد الإرسال
        else:
            await update.message.reply_text("❌ فشل في تحميل المحتوى.")

        await status_message.delete()

    except Exception as e:
        print(f"Error: {e}")
        await status_message.edit_text("❌ حدث خطأ أثناء محاولة تحميل الرابط.")

def main():
    # إنشاء مجلد التنزيلات المؤقت إذا لم يكن موجوداً
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # إضافة معالج النصوص لاستقبال الروابط
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot Started")
    app.run_polling()

if __name__ == "__main__":
    main()
