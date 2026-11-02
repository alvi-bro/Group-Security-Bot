import os
import logging
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- মেনু লেআউট ---
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
    return InlineKeyboardMarkup([row1, row2, row3, row4, row5, row6, row7, row8, row9, row10, row11])

# --- হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"✨ **𝐖𝐄𝐋𝐂𝐎𝐌𝐄, {update.effective_user.first_name}** ✨\n\n👑 **𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐆𝐫𝐨𝐮𝐩 𝐂𝐨𝐧𝐭𝐫𝐨𝐥𝐥𝐞𝐫**\n👇 নিচের মেনু থেকে সিলেক্ট করুন:"
    await update.message.reply_text(text=text, reply_markup=get_main_menu(), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "main_menu":
        text = "👑 **𝐏𝐫𝐞𝐦𝐢𝐮𝐦 𝐆𝐫𝐨𝐮𝐩 𝐂𝐨𝐧𝐭𝐫𝐨𝐥𝐥𝐞𝐫**\n👇 নিচের মেনু থেকে সিলেক্ট করুন:"
        await query.edit_message_text(text=text, reply_markup=get_main_menu(), parse_mode="Markdown")
    else:
        text = f"⚙️ **{query.data.replace('_', ' ').title()}**\n\nএই ফিচারটি শীঘ্রই আসছে!"
        back = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        await query.edit_message_text(text=text, reply_markup=back, parse_mode="Markdown")

# --- ওয়েব সার্ভার ও ওয়েবহুক লজিক ---
async def telegram_webhook(request):
    app = request.app['tg_app']
    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.update_queue.put(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return web.Response(text="OK")

async def health_check(request):
    return web.Response(text="Bot is alive!")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in Environment Variables.")
    if not WEBHOOK_URL:
        raise RuntimeError("WEBHOOK_URL is missing. Set it to your Render URL (e.g., https://my-app.onrender.com)")

    # ১. টেলিগ্রাম অ্যাপ্লিকেশন তৈরি
    tg_app = Application.builder().token(BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(CallbackQueryHandler(button_handler))

    # ২. ওয়েব সার্ভার তৈরি
    webapp = web.Application()
    webapp['tg_app'] = tg_app
    webapp.router.add_get("/", health_check)
    webapp.router.add_post("/webhook", telegram_webhook)

    # ৩. ওয়েব সার্ভার চালু (Render-এর জন্য 0.0.0.0 এবং PORT জরুরি)
    runner = web.AppRunner(webapp)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", PORT).start()
    logger.info(f"Web server listening on port {PORT}")

    # ৪. টেলিগ্রাম বট ইনিশিয়ালাইজ ও ওয়েবহুক সেট
    await tg_app.initialize()
    await tg_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook", drop_pending_updates=True)
    await tg_app.start()
    logger.info("Telegram Bot started via Webhook")

    try:
        await asyncio.Event().wait()
    finally:
        await tg_app.stop()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
