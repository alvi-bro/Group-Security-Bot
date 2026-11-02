import os
import logging
import secrets
from html import escape
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
WEBHOOK_PATH = "/webhook"

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
log = logging.getLogger("group-security-official")


def main_menu_text(name=None):
    greeting = f"✨ <b>WELCOME, {escape(name)}</b> ✨\n\n" if name else ""
    return (
        greeting
        + "🛡️ <b>GROUP SECURITY OFFICIAL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 <b>PREMIUM GROUP CONTROL CENTER</b>\n\n"
        "আপনার Telegram Group-কে নিরাপদ, পরিচ্ছন্ন ও সুন্দরভাবে "
        "পরিচালনা করতে নিচের Control Panel ব্যবহার করুন।\n\n"
        "⚡ <b>Select a feature to continue:</b>\n"
        "<i>Choose an option below to explore its settings.</i>"
    )


def get_main_menu():
    # Original two-column layout and all 22 buttons preserved.
    rows = [
        [InlineKeyboardButton("👥 Group Add", callback_data="group_add"), InlineKeyboardButton("🛡️ Mod Commands", callback_data="mod_commands")],
        [InlineKeyboardButton("👋 Welcome Set", callback_data="welcome_set"), InlineKeyboardButton("📜 Rules Set", callback_data="rules_set")],
        [InlineKeyboardButton("🔗 Link Alert", callback_data="link_alert"), InlineKeyboardButton("🤬 Bad Words Set", callback_data="bad_words_set")],
        [InlineKeyboardButton("🛡️ Anti Spam", callback_data="anti_spam"), InlineKeyboardButton("🤬 Bad Word Alert", callback_data="bad_word_alert")],
        [InlineKeyboardButton("🌙 Night Mode", callback_data="night_mode"), InlineKeyboardButton("💬 Keyword Auto Reply", callback_data="keyword_auto_reply")],
        [InlineKeyboardButton("📢 Force Subscribe", callback_data="force_subscribe"), InlineKeyboardButton("🚨 Report System", callback_data="report_system")],
        [InlineKeyboardButton("🌐 Language Filter", callback_data="language_filter"), InlineKeyboardButton("⏩ Forward Detection", callback_data="forward_detection")],
        [InlineKeyboardButton("🛡️ Captcha System", callback_data="captcha_system"), InlineKeyboardButton("🤖 Bot Msg Remove", callback_data="bot_msg_remove")],
        [InlineKeyboardButton("💻 Command Set", callback_data="command_set"), InlineKeyboardButton("✉️ SMS Reply", callback_data="sms_reply")],
        [InlineKeyboardButton("📢 Auto Post", callback_data="auto_post"), InlineKeyboardButton("📅 Loop Post", callback_data="loop_post")],
        [InlineKeyboardButton("🤖 Our Bot", callback_data="our_bot"), InlineKeyboardButton("📚 Helpline", callback_data="helpline")],
    ]
    return InlineKeyboardMarkup(rows)


FEATURES = {
    "group_add": ("👥 <b>GROUP ADD</b>", "আপনার Telegram Group-এ বটটি Add করুন এবং প্রয়োজনীয় Admin Permission দিন।", "➜ <b>Next step:</b> গ্রুপে বটকে Admin হিসেবে Promote করুন।"),
    "mod_commands": ("🛡️ <b>MODERATION COMMANDS</b>", "গ্রুপের Moderator ও Admin-দের মাধ্যমে নিরাপদ Moderation পরিচালনা করুন।", "➜ <b>Commands:</b> /ban, /mute, /unmute, /warn, /purge"),
    "welcome_set": ("👋 <b>WELCOME MESSAGE SETUP</b>", "নতুন সদস্যদের জন্য আপনার পছন্দের Welcome Message তৈরি করুন।", "➜ <b>Setup:</b> Welcome Message সেট করার সুবিধা পরবর্তী ধাপে যুক্ত হবে।"),
    "rules_set": ("📜 <b>GROUP RULES SETUP</b>", "আপনার গ্রুপের নিয়ম-কানুন লিখে সদস্যদের জন্য Rules Message সাজান।", "➜ <b>Tip:</b> সহজ ও পরিষ্কার ভাষায় গ্রুপের নিয়ম লিখুন।"),
    "link_alert": ("🔗 <b>LINK ALERT</b>", "গ্রুপে শেয়ার করা লিংক শনাক্ত করার সেটিংস।", "➜ <b>Note:</b> Link filtering automation পরবর্তী ধাপে যুক্ত হবে।"),
    "bad_words_set": ("🤬 <b>BAD WORDS SETUP</b>", "যেসব শব্দ গ্রুপে অনুমোদিত নয়, সেগুলো কমা দিয়ে আলাদা করে পাঠান।", "➜ <b>Example:</b> word1, word2, word3\n<i>সাধারণ কথাও যেন ভুল করে Block না হয়, তালিকা যাচাই করে ব্যবহার করুন।</i>"),
    "anti_spam": ("🛡️ <b>ANTI-SPAM PROTECTION</b>", "অপ্রয়োজনীয় পুনরাবৃত্ত মেসেজ ও Spam নিয়ন্ত্রণের বিভাগ।", "➜ <b>Status:</b> এই Starter UI-তে toggle logic এখনো যুক্ত হয়নি।"),
    "bad_word_alert": ("🤬 <b>BAD WORD ALERT</b>", "নিষিদ্ধ শব্দ শনাক্ত হলে Admin-দের Alert দেওয়ার বিভাগ।", "➜ <b>Note:</b> Alert delivery logic পরবর্তী ধাপে যুক্ত হবে।"),
    "night_mode": ("🌙 <b>NIGHT MODE</b>", "নির্দিষ্ট সময়ে গ্রুপের মেসেজিং সীমিত করার পরিকল্পিত সেটিংস।", "➜ <b>Note:</b> Automatic schedule চালাতে scheduler প্রয়োজন।"),
    "keyword_auto_reply": ("💬 <b>KEYWORD AUTO REPLY</b>", "নির্দিষ্ট Keyword পেলে স্বয়ংক্রিয় উত্তর দেওয়ার ব্যবস্থা।", "➜ <b>Note:</b> Keyword ও reply সংরক্ষণের logic পরবর্তী ধাপে যুক্ত হবে।"),
    "force_subscribe": ("📢 <b>FORCE SUBSCRIBE</b>", "গ্রুপে অংশগ্রহণের আগে নির্দিষ্ট Channel-এ Join করার শর্ত ব্যবস্থাপনা।", "➜ <b>Requirement:</b> বটকে Channel ও Group-এ প্রয়োজনীয় permission দিতে হবে।"),
    "report_system": ("🚨 <b>REPORT SYSTEM</b>", "সদস্যরা সমস্যাযুক্ত মেসেজ Report করতে পারবেন—এমন ব্যবস্থার বিভাগ।", "➜ <b>Tip:</b> Report review-এর জন্য Admin notification setup প্রয়োজন।"),
    "language_filter": ("🌐 <b>LANGUAGE FILTER</b>", "গ্রুপের জন্য ভাষাভিত্তিক moderation policy নির্ধারণের বিভাগ।", "➜ <b>Note:</b> Language detection logic পরবর্তী ধাপে যুক্ত হবে।"),
    "forward_detection": ("⏩ <b>FORWARD DETECTION</b>", "Forward করা মেসেজ শনাক্ত ও প্রয়োজন অনুযায়ী নিয়ন্ত্রণের সেটিংস।", "➜ <b>Requirement:</b> Auto-delete করতে Delete Messages permission প্রয়োজন।"),
    "captcha_system": ("🛡️ <b>CAPTCHA VERIFICATION</b>", "নতুন সদস্যদের জন্য Join Verification ব্যবস্থার বিভাগ।", "➜ <b>Note:</b> পূর্ণাঙ্গ CAPTCHA flow এখনো সক্রিয় নয়।"),
    "bot_msg_remove": ("🤖 <b>BOT MESSAGE REMOVE</b>", "গ্রুপে অন্য Bot-এর পাঠানো মেসেজ নিয়ন্ত্রণের বিভাগ।", "➜ <b>Requirement:</b> প্রয়োজনীয় Admin permission দিতে হবে।"),
    "command_set": ("💻 <b>COMMAND SETUP</b>", "আপনার গ্রুপের জন্য Custom command ও response সাজানোর বিভাগ।", "➜ <b>Note:</b> Custom command storage logic পরবর্তী ধাপে যুক্ত হবে।"),
    "sms_reply": ("✉️ <b>SMS REPLY</b>", "নির্দিষ্ট trigger-এর ভিত্তিতে স্বয়ংক্রিয় text reply পরিচালনার বিভাগ।", "➜ <b>Note:</b> এটি Telegram reply feature; SMS পাঠানোর সুবিধা নয়।"),
    "auto_post": ("📢 <b>AUTO POST</b>", "নির্ধারিত সময়ে গ্রুপে বা Channel-এ পোস্ট প্রকাশের পরিকল্পিত বিভাগ।", "➜ <b>Note:</b> Scheduled posting চালাতে scheduler প্রয়োজন।"),
    "loop_post": ("📅 <b>LOOP POST</b>", "নির্দিষ্ট বিরতিতে কোনো পোস্ট পুনরায় প্রকাশের পরিকল্পিত বিভাগ।", "➜ <b>Note:</b> Recurring scheduler এখনো সক্রিয় নয়।"),
    "our_bot": ("🤖 <b>ABOUT OUR BOT</b>", "GROUP SECURITY OFFICIAL — Premium Group Management Assistant.", "🛡️ <i>Designed to help admins manage their Telegram communities.</i>"),
    "helpline": ("📚 <b>HELP & SUPPORT</b>", "বট ব্যবহার বা সেটআপে সমস্যা হলে Bot Owner বা Support Admin-এর সঙ্গে যোগাযোগ করুন।", "➜ <b>Quick help:</b> /start অথবা /menu"),
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if update.effective_message:
        await update.effective_message.reply_text(
            main_menu_text(user.first_name if user else None),
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "main_menu":
        await query.edit_message_text(
            main_menu_text(query.from_user.first_name),
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.HTML,
        )
        return

    item = FEATURES.get(data)
    if item:
        title, description, note = item
        text = (
            "✨ <b>GROUP SECURITY OFFICIAL</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{title}\n\n{description}\n\n{note}\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>PREMIUM GROUP CONTROL PANEL</i>"
        )
    else:
        text = "⚙️ <b>FEATURE NOT FOUND</b>\n\nMain Menu থেকে অন্য একটি অপশন নির্বাচন করুন।"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙  BACK TO MAIN MENU", callback_data="main_menu")
    ]])
    await query.edit_message_text(
        text, reply_markup=keyboard, parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def error_handler(update, context):
    log.exception("Telegram handler error", exc_info=context.error)


async def health_check(request):
    return web.json_response({
        "status": "ok",
        "service": "GROUP SECURITY OFFICIAL",
        "mode": "webhook",
    })


async def webhook_handler(request):
    application = request.app["telegram_app"]
    if WEBHOOK_SECRET:
        supplied = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secrets.compare_digest(supplied, WEBHOOK_SECRET):
            raise web.HTTPForbidden(text="Invalid webhook secret")
    try:
        payload = await request.json()
        update = Update.de_json(payload, application.bot)
        await application.update_queue.put(update)
    except Exception:
        log.exception("Invalid Telegram update")
        raise web.HTTPBadRequest(text="Invalid Telegram update")
    return web.json_response({"ok": True})


async def on_startup(app):
    application = app["telegram_app"]
    await application.initialize()
    await application.start()
    webhook_args = {
        "url": f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        "allowed_updates": Update.ALL_TYPES,
        "drop_pending_updates": False,
    }
    if WEBHOOK_SECRET:
        webhook_args["secret_token"] = WEBHOOK_SECRET
    await application.bot.set_webhook(**webhook_args)
    log.info("Webhook configured: %s%s", WEBHOOK_URL, WEBHOOK_PATH)


async def on_cleanup(app):
    application = app["telegram_app"]
    try:
        await application.bot.delete_webhook(drop_pending_updates=False)
    except Exception:
        log.exception("Webhook cleanup failed")
    await application.stop()
    await application.shutdown()


def create_app():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing. Add it in Render Environment Variables.")
    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL is missing. Add your Render service URL.")

    telegram_app = Application.builder().token(BOT_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.add_handler(CommandHandler("menu", start))
    telegram_app.add_handler(CallbackQueryHandler(button_handler))
    telegram_app.add_error_handler(error_handler)

    app = web.Application()
    app["telegram_app"] = telegram_app
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_post(WEBHOOK_PATH, webhook_handler)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(create_app(), host="0.0.0.0", port=PORT)
