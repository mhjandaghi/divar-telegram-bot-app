from typing import Final
from telegram import Update, InlineQueryResultPhoto
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    InlineQueryHandler,
    filters,
)
from mongo_client import AdsMongoClient

# تنظیمات اولیه
BOT_TOKEN: Final = "<BOT_TOKEN>"
CATEGORY, PHOTO, DESCRIPTION = range(3)
db_client = AdsMongoClient("localhost", 27017)
dev_ids = [92129627, 987654321]

# هندلر دستور /start
async def start_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="سلام، من ربات ثبت آگهی هستم. برای ثبت آگهی جدید از دستور /add_advertising استفاده کنید.",
        reply_to_message_id=update.effective_message.id,
    )

# هندلر دستور /add_category
async def add_category_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in dev_ids:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="شما دسترسی لازم برای اجرای این دستور را ندارید.",
            reply_to_message_id=update.effective_message.id,
        )
        return

    category = " ".join(context.args)
    if not category:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="لطفاً نام دسته‌بندی را وارد کنید.",
            reply_to_message_id=update.effective_message.id,
        )
        return

    db_client.add_category(category)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"دسته‌بندی '{category}' با موفقیت اضافه شد.",
        reply_to_message_id=update.effective_message.id,
    )

# هندلر دستور /add_advertising
async def add_advertising_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    categories = db_client.get_categories()
    text = "لطفاً از بین دسته‌بندی‌های زیر یکی را انتخاب کنید:\n" + "\n".join(categories)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=text,
        reply_to_message_id=update.effective_message.id,
    )
    return CATEGORY

async def choice_category_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    category = update.effective_message.text
    categories = db_client.get_categories()

    if category not in categories:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="دسته‌بندی انتخابی نامعتبر است. لطفاً مجدداً تلاش کنید.",
            reply_to_message_id=update.effective_message.id,
        )
        return CATEGORY

    context.user_data["category"] = category
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="لطفاً عکس آگهی خود را ارسال کنید.",
        reply_to_message_id=update.effective_message.id,
    )
    return PHOTO

async def photo_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo = update.effective_message.photo[-1].file_id
    context.user_data["photo_url"] = photo

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="لطفاً توضیحات آگهی خود را وارد کنید.",
        reply_to_message_id=update.effective_message.id,
    )
    return DESCRIPTION

async def description_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    category = context.user_data.get("category")
    photo_url = context.user_data.get("photo_url")
    description = update.effective_message.text

    if not (category and photo_url and description):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="خطا در ثبت اطلاعات آگهی. لطفاً دوباره تلاش کنید.",
            reply_to_message_id=update.effective_message.id,
        )
        return ConversationHandler.END

    db_client.add_advertising(user_id=user_id, photo_url=photo_url, category=category, description=description)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="آگهی شما با موفقیت ثبت شد.",
        reply_to_message_id=update.effective_message.id,
    )
    return ConversationHandler.END

async def cancel_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="عملیات ثبت آگهی لغو شد.",
        reply_to_message_id=update.effective_message.id,
    )
    return ConversationHandler.END

async def my_ads_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ads = db_client.get_user_ads(update.effective_user.id)

    if not ads:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="شما هیچ آگهی ثبت نکرده‌اید.",
            reply_to_message_id=update.effective_message.id,
        )
        return

    for ad in ads:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=ad["photo_url"],
            caption=ad["description"] + "\n\n" +
                    "برای حذف آگهی از دستور زیر استفاده کنید:\n\n" +
                    f"/delete_ad {ad['id']}",
            reply_to_message_id=update.effective_message.id,
        )


async def delete_ad_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="لطفاً آیدی آگهی مورد نظر را وارد کنید. مثال: /delete_ad 12345",
            reply_to_message_id=update.effective_message.id,
        )
        return

    ad_id = context.args[0]
    db_client.delete_advertising(user_id=user_id, ad_id=ad_id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="آگهی با موفقیت حذف شد.",
        reply_to_message_id=update.effective_message.id,
    )

async def inline_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query

    if not query:
        await context.bot.answer_inline_query(
            inline_query_id=update.inline_query.id,
            results=[],
            cache_time=1,
        )
        return

    ads = db_client.get_ads_by_category(query)
    results = [
        InlineQueryResultPhoto(
            id=ad["id"],
            title=ad["description"],
            photo_url=ad["photo_url"],
            thumbnail_url=ad["photo_url"],
            caption=ad["description"],
        )
        for ad in ads
    ]

    await context.bot.answer_inline_query(
        inline_query_id=update.inline_query.id,
        results=results,
        cache_time=1,
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command_handler))
    app.add_handler(CommandHandler("add_category", add_category_command_handler))
    app.add_handler(CommandHandler("my_ads", my_ads_command_handler))
    app.add_handler(CommandHandler("delete_ad", delete_ad_command_handler))
    app.add_handler(InlineQueryHandler(inline_query_handler))
    app.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("add_advertising", add_advertising_command_handler)],
            states={
                CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_category_message_handler)],
                PHOTO: [MessageHandler(filters.PHOTO, photo_message_handler)],
                DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description_message_handler)],
            },
            fallbacks=[CommandHandler("cancel", cancel_command_handler)],
            allow_reentry=True,
        )
    )

    app.run_polling()
