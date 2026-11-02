import os
import logging
import asyncio
from aiohttp import web
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Configuration ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
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
    return InlineKeyboardMarkup([row1, row2, row3, row4, row5, row6, row7, row8, row9, row10, row11])

# --- Handlers ---
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

# --- Dummy Web Server for Render Health Check ---
async def health_check(request):
    return web.Response(text="Bot is running with Polling!")

async def run_dummy_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Dummy web server started on port {PORT}")

# --- Main Runner ---
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in Environment Variables.")

    # ১. Render-এর পোর্ট চেক পাস করার জন্য ছোট ওয়েব সার্ভার চালু
    await run_dummy_server()

    # ২. টেলিগ্রাম অ্যাপ্লিকেশন তৈরি
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # ৩. বট চালু (Polling Mode)
    logger.info("Starting bot in Polling mode...")
    
    # Webhook ডিলিট করে পোলিং শুরু করা (নিশ্চিত করার জন্য)
    await app.bot.delete_webhook(drop_pending_updates=True)
    
    # Polling শুরু
    await app.initialize()
    await app.updater.start_polling()
    await app.start()

    # ৪. প্রোগ্রাম চলমান রাখা
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
