import os
import logging
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
PORT = int(os.getenv("PORT", "10000"))
# Render-এ ডিপ্লয় করার পর আপনার অ্যাপের URL এখানে বসাতে হবে (যেমন: https://my-bot.onrender.com)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://group-security-bot-xtkp.onrender.com") 

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Main Menu Layout ---
def get_main_menu():
    row1 = [InlineKeyboardButton("👥 Group Add", callback_data="group_add"), InlineKeyboardButton("🛡️ Mod Commands", callback_data="mod_commands")]
    row2 = [InlineKeyboardButton("👋 Welcome Set", callback_data="welcome_set"), InlineKeyboardButton("📜 Rules Set", callback_data="rules_set")]
    row3 = [InlineKeyboardButton("🔗 Link Alert", callback_data="link_alert"), InlineKeyboardButton("🤬 Bad Words Set", callback_data="bad_words_set")]
    row4 = [InlineKeyboardButton("🛡️ Anti Spam", callback_data="anti_spam"), InlineKeyboardButton("🤬 Bad Word Alert", callback_data="bad_word_alert")]
    row5 = [InlineKeyboardButton("🌙 Night Mode", callback_data="night_mode"), InlineKeyboardButton("💬 Keyword Auto Reply", callback_data="keyword_auto_reply")]
    row6 = [InlineKeyboardButton("📢 Force Subscribe", callback_data="force_subscribe"), InlineKeyboardButton("🚨 Report System", callback_data="report_system")]
    row7 = [InlineKeyboardButton("🌐 Language Filter", callback_data="language_filter"), InlineKeyboardButton("⏩ Forward Detection", callback_data="forward_detection")]
    row8 = [InlineKeyboardButton("🛡️ Captcha System", callback_data="captcha_system"), InlineKeyboardButton("🤖 Bot Msg Remove", callback_data="bot_msg_remove")]
    row9 = [InlineKeyboardButton("💻 Command Set", callback_data="command_set"), InlineKeyboardButton("✉️ SMS Reply", callback_data="sms_reply")]
    row10 = [InlineKeyboardButton("📢 Auto Post", callback_data="auto_post"), InlineKeyboardButton("📅 Loop Post", callback_data="loop_post")]
    row11 = [InlineKeyboardButton("🤖 Our Bot", callback_data="our_bot"), InlineKeyboardButton("📚 Helpline", callback_data="helpline")]

    keyboard = [row1, row2, row3, row4, row5, row6, row7, row8, row9, row10, row11]
    return InlineKeyboardMarkup(keyboard)

# --- Command & Callback Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"✨ **𝐖𝐄𝐋𝐂𝐎𝐌𝐄, {user.first_name}** ✨\n\n"
        "👑 **𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐆𝐫𝐨𝐮𝐩 𝐂𝐨𝐧𝐭𝐫𝐨𝐥𝐥𝐞𝐫 𝐁𝐨𝐭**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন।\n"
        "👇 **𝐂𝐥𝐢𝐜𝐤 𝐚 𝐛𝐮𝐭𝐭𝐨𝐧 𝐭𝐨 𝐜𝐨𝐧𝐭𝐢𝐧𝐮𝐞:**"
    )
    await update.message.reply_text(text=text, reply_markup=get_main_menu(), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    descriptions = {
        "group_add": "👥 **𝐆𝐫𝐨𝐮𝐩 𝐀𝐝𝐝**\n\nAdd the bot to your group to start managing it.",
        "mod_commands": "🛡️ **𝐌𝐨𝐝 𝐂𝐨𝐦𝐦𝐚𝐧𝐝𝐬**\n\nManage your group moderators here.",
        "welcome_set": "👋 **𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐒𝐞𝐭**\n\nSet a custom welcome message for new members.",
        "rules_set": "📜 **𝐑𝐮𝐥𝐞𝐬 𝐒𝐞𝐭**\n\nSet rules for your group.",
        "link_alert": "🔗 **𝐋𝐢𝐧𝐤 𝐀𝐥𝐞𝐫𝐭**\n\nGet notified when someone sends a link.",
        "bad_words_set": "🤬 **𝐁𝐚𝐝 𝐖𝐨𝐫𝐝𝐬 𝐒𝐞𝐭**\n\nAdd words to the profanity filter.",
        "anti_spam": "🛡️ **𝐀𝐧𝐭𝐢 𝐒𝐩𝐚𝐦**\n\nEnable or disable anti-spam protection.",
        "bad_word_alert": "🤬 **𝐁𝐚𝐝 𝐖𝐨𝐫𝐝 𝐀𝐥𝐞𝐫𝐭**\n\nGet alerts when bad words are detected.",
        "night_mode": "🌙 **𝐍𝐢𝐠𝐡𝐭 𝐌𝐨𝐝𝐞**\n\nLock the group during specific hours.",
        "keyword_auto_reply": "💬 **𝐊𝐞𝐲𝐰𝐨𝐫𝐝 𝐀𝐮𝐭𝐨 𝐑𝐞𝐩𝐥𝐲**\n\nSet up automatic replies for specific keywords.",
        "force_subscribe": "📢 **𝐅𝐨𝐫𝐜𝐞 𝐒𝐮𝐛𝐬𝐜𝐫𝐢𝐛𝐞**\n\nForce users to join a channel before messaging.",
        "report_system": "🚨 **𝐑𝐞𝐩𝐨𝐫𝐭 𝐒𝐲𝐬𝐭𝐞𝐦**\n\nAllow users to report rule breakers.",
        "language_filter": "🌐 **𝐋𝐚𝐧𝐠𝐮𝐚𝐠𝐞 𝐅𝐢𝐥𝐭𝐞𝐫**\n\nFilter out specific languages.",
        "forward_detection": "⏩ **𝐅𝐨𝐫𝐰𝐚𝐫𝐝 𝐃𝐞𝐭𝐞𝐜𝐭𝐢𝐨𝐧**\n\nDetect and delete forwarded messages.",
        "captcha_system": "🛡️ **𝐂𝐚𝐩𝐭𝐜𝐡𝐚 𝐒𝐲𝐬𝐭𝐞𝐦**\n\nVerify new members with a captcha.",
        "bot_msg_remove": "🤖 **𝐁𝐨𝐭 𝐌𝐬𝐠 𝐑𝐞𝐦𝐨𝐯𝐞**\n\nAutomatically delete messages from other bots.",
        "command_set": "💻 **𝐂𝐨𝐦𝐦𝐚𝐧𝐝 𝐒𝐞𝐭**\n\nCustomize bot commands.",
        "sms_reply": "✉️ **𝐒𝐌𝐒 𝐑𝐞𝐩𝐥𝐲**\n\nSetup SMS auto-replies.",
        "auto_post": "📢 **𝐀𝐮𝐭𝐨 𝐏𝐨𝐬𝐭**\n\nAutomatically post from channels.",
        "loop_post": "📅 **𝐋𝐨𝐨𝐩 𝐏𝐨𝐬𝐭**\n\nSet looping scheduled posts.",
        "our_bot": "🤖 **𝐎𝐮𝐫 𝐁𝐨𝐭**\n\nInformation about this bot.",
        "helpline": "📚 **𝐇𝐞𝐥𝐩𝐥𝐢𝐧𝐞**\n\nContact support for help."
    }
    
    response_text = descriptions.get(data, "⚙️ **𝐅𝐞𝐚𝐭𝐮𝐫𝐞 𝐜𝐨𝐦𝐢𝐧𝐠 𝐬𝐨𝐨𝐧!**")
    back_button = [[InlineKeyboardButton("🔙 𝐁𝐚𝐜𝐤 𝐭𝐨 𝐌𝐞𝐧𝐮", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(back_button)

    await query.edit_message_text(text=response_text, reply_markup=reply_markup, parse_mode="Markdown")

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "👑 **𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐆𝐫𝐨𝐮𝐩 𝐂𝐨𝐧𝐭𝐫𝐨𝐥𝐥𝐞𝐫 𝐁𝐨𝐭**\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "নিচের মেনু থেকে আপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন।\n"
        "👇 **𝐂𝐥𝐢𝐜𝐤 𝐚 𝐛𝐮𝐭𝐭𝐨𝐧 𝐭𝐨 𝐜𝐨𝐧𝐭𝐢𝐧𝐮𝐞:**"
    )
    await query.edit_message_text(text=text, reply_markup=get_main_menu(), parse_mode="Markdown")

# --- Webhook & Web Server Logic ---
async def webhook_handler(request: web.Request) -> web.Response:
    """Processes updates from Telegram."""
    application = request.app['telegram_app']
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
    return web.Response(text="OK")

async def health_check(request: web.Request) -> web.Response:
    """Render health check endpoint."""
    return web.Response(text="Bot is running!")

async def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN is missing. Set it in Render Environment Variables.")
    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL is missing. Set it in Render Environment Variables (e.g., https://your-app.onrender.com).")

    # Initialize Telegram Application
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(back_to_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Initialize Web Server
    webapp = web.Application()
    webapp['telegram_app'] = application
    webapp.router.add_get("/", health_check)
    webapp.router.add_post("/webhook", webhook_handler)

    # Start Web Server
    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server listening on port {PORT}")

    # Start Telegram Bot with Webhook
    await application.initialize()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    await application.start()
    logger.info("Telegram Bot started via Webhook")

    # Keep the script running
    try:
        await asyncio.Event().wait()
    finally:
        await application.stop()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
