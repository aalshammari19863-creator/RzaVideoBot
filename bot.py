async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    url = update.message.text
    
    register_user(user_id)
    
    # 🚨 تحقق دقيق وشامل لروابط سناب شات بجميع صيغها وحظرها عن العامة
    is_snapchat = "snapchat.com" in url
    if is_snapchat and user_id != ADMIN_ID:
        fail_msg = await update.message.reply_text("❌ عذراً، ميزة تحميل مقاطع سناب شات غير مدعومة حالياً للعامة.")
        asyncio.create_task(delete_message_after_delay(context, chat_id, fail_msg.message_id))
        asyncio.create_task(delete_message_after_delay(context, chat_id, update.message.message_id, delay=5))
        return

    # الشرط المعدل والمحدث ليتعرف على جميع الروابط بشكل صحيح
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

    # 🔗 معالجة منصة تيك توك (الكود القديم للجميع)
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
