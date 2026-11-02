import os, re, sqlite3, logging, asyncio
from datetime import datetime, timezone
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ChatMemberHandler, ContextTypes, filters
)

TOKEN = os.getenv("BOT_TOKEN", "").strip()
DB_PATH = os.getenv("DB_PATH", "group_controller.db")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
HELP_URL = os.getenv("HELP_URL", "https://t.me/")
BOT_ABOUT = os.getenv("BOT_ABOUT", "GROUP CONTROLLER — Group management bot")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
log = logging.getLogger("group-controller")

# Apply premium styling centrally so no hard-coded interface message is missed.
from telegram import Message, Bot, CallbackQuery

_original_reply_text = Message.reply_text
async def _premium_reply_text(self, text, *args, **kwargs):
    return await _original_reply_text(self, _premium_text(text), *args, **kwargs)
Message.reply_text = _premium_reply_text

_original_edit_text = Message.edit_text
async def _premium_edit_text(self, text, *args, **kwargs):
    return await _original_edit_text(self, _premium_text(text), *args, **kwargs)
Message.edit_text = _premium_edit_text

_original_query_edit = CallbackQuery.edit_message_text
async def _premium_query_edit(self, text, *args, **kwargs):
    return await _original_query_edit(self, _premium_text(text), *args, **kwargs)
CallbackQuery.edit_message_text = _premium_query_edit

_original_query_answer = CallbackQuery.answer
async def _premium_query_answer(self, text=None, *args, **kwargs):
    return await _original_query_answer(self, _premium_text(text), *args, **kwargs)
CallbackQuery.answer = _premium_query_answer

_original_send_message = Bot.send_message
async def _premium_send_message(self, chat_id, text, *args, **kwargs):
    return await _original_send_message(self, chat_id, _premium_text(text), *args, **kwargs)
Bot.send_message = _premium_send_message

_original_button_init = InlineKeyboardButton.__init__
def _premium_button_init(self, text, *args, **kwargs):
    return _original_button_init(self, _premium_text(text), *args, **kwargs)
InlineKeyboardButton.__init__ = _premium_button_init


# Premium Unicode bold formatter for all bot interface text.
_BOLD_MAP = str.maketrans(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
    "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙"
    "𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳"
    "𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
)

def _premium_text(value):
    if not isinstance(value, str):
        return value
    # Keep HTML markup and code spans intact so Telegram parsing and commands work.
    parts = re.split(r"(<code>.*?</code>|<pre>.*?</pre>|<[^>]+>)", value, flags=re.I | re.S)
    return "".join(
        part if (part.startswith("<") and part.endswith(">"))
        else part.translate(_BOLD_MAP)
        for part in parts
    )


DEFAULTS = {
    "welcome": "👋 Welcome {name}!\nThank you for joining our group.",
    "rules": "📜 Group Rules:\n1. Respect everyone\n2. Do not spam\n3. Do not share irrelevant links",
    "link_alert": "0", "anti_spam": "0", "bad_word_alert": "1",
    "night_mode": "0", "force_subscribe": "0", "report_system": "1",
    "language_filter": "0", "forward_detection": "0", "captcha": "0",
    "bot_msg_remove": "0", "bad_words": "", "keywords": "",
    "custom_commands": "", "sms_reply": "", "auto_post": "",
    "loop_post": "", "required_channel": "", "spam_limit": "5",
    "spam_window": "8"
}

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("""CREATE TABLE IF NOT EXISTS settings
              (chat_id INTEGER, key TEXT, value TEXT,
               PRIMARY KEY(chat_id,key))""")
db.execute("""CREATE TABLE IF NOT EXISTS warnings
              (chat_id INTEGER, user_id INTEGER, count INTEGER,
               PRIMARY KEY(chat_id,user_id))""")
db.commit()

pending = {}  # (chat_id, user_id) -> setting key
spam_cache = {}  # (chat_id,user_id) -> timestamps


def get_setting(chat_id, key):
    row = db.execute("SELECT value FROM settings WHERE chat_id=? AND key=?",
                     (chat_id, key)).fetchone()
    return row[0] if row else DEFAULTS.get(key, "")


def set_setting(chat_id, key, value):
    db.execute("""INSERT INTO settings(chat_id,key,value) VALUES(?,?,?)
                  ON CONFLICT(chat_id,key) DO UPDATE SET value=excluded.value""",
               (chat_id, key, str(value)))
    db.commit()


def is_on(chat_id, key):
    return get_setting(chat_id, key) == "1"


def main_keyboard():
    rows = [
        [("👥 Group Add", "add"), ("🛡️ Mod Commands", "mods")],
        [("👋 Welcome Set", "welcome"), ("📜 Rules Set", "rules")],
        [("🔗 Link Alert", "link_alert"), ("🤬 Bad Words Set", "bad_words")],
        [("🛡️ Anti Spam", "anti_spam"), ("🤬 Bad Word Alert", "bad_word_alert")],
        [("🌙 Night Mode", "night_mode"), ("💬 Keyword Auto Reply", "keywords")],
        [("📢 Force Subscribe", "force_subscribe"), ("🚨 Report System", "report_system")],
        [("🌐 Language Filter", "language_filter"), ("⏩ Forward Detection", "forward_detection")],
        [("🛡️ Captcha System", "captcha"), ("🤖 Bot Msg Remove", "bot_msg_remove")],
        [("💻 Command Set", "custom_commands"), ("✉️ SMS Reply", "sms_reply")],
        [("📣 Auto Post", "auto_post"), ("📅 Loop Post", "loop_post")],
        [("🤖 Our Bot", "about"), ("📚 Helpline", "help")]
    ]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t, callback_data=f"menu:{k}") for t, k in row]
        for row in rows
    ])


def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Control Panel",
                                                       callback_data="menu:home")]])


async def admin_ok(update: Update, chat_id=None):
    user = update.effective_user
    chat = update.effective_chat
    target = chat_id or (chat.id if chat else None)
    if not user or not target:
        return False
    if OWNER_ID and user.id == OWNER_ID:
        return True
    try:
        member = await update.get_bot().get_chat_member(target, user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


async def show_panel(message, chat_id):
    title = (
        "👑 <b>GROUP CONTROLLER OFFICIAL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️ <b>Premium Group Control Panel</b>\n"
        f"🆔 <code>{chat_id}</code>\n\n"
        "Choose the setting you need using the buttons below."
    )
    await message.reply_text(title, reply_markup=main_keyboard(), parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👑 <b>GROUP CONTROLLER OFFICIAL</b>\n\n"
        "I can help you manage and moderate your group.\n\n"
        "1️⃣ Add me to your group\n"
        "2️⃣ Grant the required admin permissions\n"
        "3️⃣ Type /panel in your group to open the control panel"
    )
    await update.effective_message.reply_text(msg, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add to Group",
                url=f"https://t.me/{context.bot.username}?startgroup=true")],
            [InlineKeyboardButton("📚 Help", callback_data="menu:help")]
        ]))


async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        await update.effective_message.reply_text(
            "Add the bot to your group, then type /panel there to open the control panel."
        )
        return
    if not await admin_ok(update):
        await update.effective_message.reply_text("⛔ Only group administrators can use this panel.")
        return
    await show_panel(update.effective_message, chat.id)


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data.split(":", 1)[1]
    chat_id = q.message.chat.id
    user_id = q.from_user.id

    if data == "home":
        if not await admin_ok(update, chat_id):
            await q.answer("Only group administrators can use this panel.", show_alert=True)
            return
        await q.edit_message_text(
            "👑 <b>GROUP CONTROLLER OFFICIAL</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ Premium Group Control Panel\n\nChoose a setting.",
            parse_mode="HTML", reply_markup=main_keyboard())
        return

    if data in ("help", "about", "add", "mods"):
        pages = {
            "help": "📚 <b>HELP CENTER</b>\n\n/panel — Control Panel\n/rules — Group Rules\n/report — Report to an administrator\n/id — Chat and User ID\n\nModeration: /ban, /mute, /unmute, /warn, /purge\n\nThe bot must have the required admin permissions.",
            "about": "🤖 <b>GROUP CONTROLLER</b>\n\nPremium Telegram Group Management Bot.\nReady to host on Render and GitHub.",
            "add": "👥 <b>ADD GROUP</b>\n\nAdd the bot to your group, grant admin permissions, then run /panel.",
            "mods": "🛡️ <b>MOD COMMANDS</b>\n\nReply to a member's message and use:\n/ban — Ban the member\n/mute — Mute the member\n/unmute — Unmute the member\n/warn — Warning\n/purge — Delete messages from the replied message through the current message"
        }
        await q.edit_message_text(pages[data], parse_mode="HTML", reply_markup=back_keyboard())
        return

    if not await admin_ok(update, chat_id):
        await q.answer("⛔ Only group administrators can change these settings.", show_alert=True)
        return

    toggles = {
        "link_alert": ("🔗 Link Alert", "Delete messages containing links and send a notice."),
        "anti_spam": ("🛡️ Anti Spam", "Limit users who send too many messages too quickly."),
        "bad_word_alert": ("🤬 Bad Word Alert", "Send an alert when a blocked word is detected."),
        "night_mode": ("🌙 Night Mode", "Night Mode is currently a saved setting only; automatic overnight restrictions are not implemented."),
        "force_subscribe": ("📢 Force Subscribe", "Check whether members have joined the required channel."),
        "report_system": ("🚨 Report System", "Enable or disable the /report command for members."),
        "language_filter": ("🌐 Language Filter", "Language-specific filter words still need to be configured."),
        "forward_detection": ("⏩ Forward Detection", "Detect forwarded messages and send a notice."),
        "captcha": ("🛡️ Captcha System", "Show a verification button to new members."),
        "bot_msg_remove": ("🤖 Bot Msg Remove", "Option for cleaning up service messages sent by bots.")
    }
    if data in toggles:
        title, desc = toggles[data]
        new = "0" if is_on(chat_id, data) else "1"
        set_setting(chat_id, data, new)
        state = "ON ✅" if new == "1" else "OFF ❌"
        await q.edit_message_text(
            f"<b>{title}</b>\n\n{desc}\n\nCurrent status: <b>{state}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Toggle", callback_data=f"menu:{data}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="menu:home")]
            ]))
        return

    prompts = {
        "welcome": ("👋 Welcome Message", "Send the welcome message for new members. Use {name} to insert the member's name."),
        "rules": ("📜 Group Rules", "Send the group rules."),
        "bad_words": ("🤬 Bad Words", "Send blocked words separated by commas. Example: word1, word2"),
        "keywords": ("💬 Keyword Auto Reply", "Send keywords and replies in this format:\nhello = Hello!\nprice = Please contact admin"),
        "custom_commands": ("💻 Custom Commands", "Send custom commands in this format:\nstartinfo = Welcome to our group\nhelpdesk = Contact admin"),
        "sms_reply": ("✉️ SMS Reply", "Send the automatic reply text. Type /clearreply to turn it off."),
        "auto_post": ("📣 Auto Post", "Send the post text for Auto Post. Type /clearpost to turn it off."),
        "loop_post": ("📅 Loop Post", "Send the text for Loop Post. This version only saves the text; scheduled posting requires a configured job queue."),
        "force_subscribe": ("📢 Force Subscribe Channel", "Send the channel username, for example @mychannel. The channel must be public and the bot must be added to it.")
    }
    if data in prompts:
        title, desc = prompts[data]
        pending[(chat_id, user_id)] = data
        await q.edit_message_text(
            f"<b>{title}</b>\n\n{desc}\n\n"
            "Now send the next message in the group.",
            parse_mode="HTML", reply_markup=back_keyboard())
        return


async def receive_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not chat or chat.type == "private" or not user:
        return
    key = pending.get((chat.id, user.id))
    if not key:
        return
    if not await admin_ok(update):
        pending.pop((chat.id, user.id), None)
        return
    value = msg.text or msg.caption or ""
    if key == "force_subscribe":
        value = value.strip()
        if not value.startswith("@"):
            await msg.reply_text("Send the channel username starting with @.")
            return
        set_setting(chat.id, "required_channel", value)
        set_setting(chat.id, key, "1")
    else:
        set_setting(chat.id, key, value)
    pending.pop((chat.id, user.id), None)
    await msg.reply_text(f"✅ <b>{key.replace('_',' ').title()}</b> has been saved.",
                         parse_mode="HTML", reply_markup=main_keyboard())


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.effective_message.reply_text(get_setting(chat_id, "rules"))


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not is_on(chat.id, "report_system"):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("Reply to the message you want to report and type /report.")
        return
    admins = await context.bot.get_chat_administrators(chat.id)
    target = update.effective_message.reply_to_message
    for a in admins:
        if not a.user.is_bot:
            try:
                await context.bot.send_message(a.user.id,
                    f"🚨 Report in {chat.title}\nFrom: {update.effective_user.mention_html()}\n"
                    f"Message: {target.text or target.caption or '[media]'}",
                    parse_mode="HTML")
            except Exception:
                pass
    await update.effective_message.reply_text("✅ The report has been sent to the administrators.")


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"Chat ID: <code>{update.effective_chat.id}</code>\n"
        f"User ID: <code>{update.effective_user.id}</code>",
        parse_mode="HTML")


async def clear_setting(update, context, key):
    chat = update.effective_chat
    if not await admin_ok(update):
        return
    set_setting(chat.id, key, "")
    await update.effective_message.reply_text("✅ The setting has been cleared.")


async def clearreply(update, context):
    await clear_setting(update, context, "sms_reply")


async def clearpost(update, context):
    await clear_setting(update, context, "auto_post")


async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    cmd = msg.text.split()[0].split("@")[0].lower()
    if not await admin_ok(update):
        await msg.reply_text("⛔ Only administrators can use this command.")
        return
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if cmd == "/purge":
        if not msg.reply_to_message:
            await msg.reply_text("Reply to the message where deletion should begin, then use /purge.")
            return
        start_id = msg.reply_to_message.message_id
        end_id = msg.message_id
        deleted = 0
        for mid in range(start_id, end_id + 1):
            try:
                await context.bot.delete_message(chat.id, mid)
                deleted += 1
            except Exception:
                pass
        return
    if not target:
        await msg.reply_text("Reply to a member's message to use this command.")
        return
    if cmd == "/ban":
        await context.bot.ban_chat_member(chat.id, target.id)
        await msg.reply_text(f"⛔ {target.first_name} has been banned.")
    elif cmd == "/mute":
        await context.bot.restrict_chat_member(chat.id, target.id,
            ChatPermissions(can_send_messages=False))
        await msg.reply_text(f"🔇 {target.first_name} has been muted.")
    elif cmd == "/unmute":
        await context.bot.restrict_chat_member(chat.id, target.id,
            ChatPermissions(can_send_messages=True, can_send_audios=True,
            can_send_documents=True, can_send_photos=True, can_send_videos=True,
            can_send_video_notes=True, can_send_voice_notes=True,
            can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True))
        await msg.reply_text(f"🔊 {target.first_name} has been unmuted.")
    elif cmd == "/warn":
        row = db.execute("SELECT count FROM warnings WHERE chat_id=? AND user_id=?",
                         (chat.id, target.id)).fetchone()
        count = (row[0] if row else 0) + 1
        db.execute("""INSERT INTO warnings(chat_id,user_id,count) VALUES(?,?,?)
                      ON CONFLICT(chat_id,user_id) DO UPDATE SET count=excluded.count""",
                   (chat.id, target.id, count))
        db.commit()
        await msg.reply_text(f"⚠️ {target.first_name}: Warning {count}/3")
        if count >= 3:
            await context.bot.ban_chat_member(chat.id, target.id)
            await msg.reply_text("⛔ The member has been banned after receiving 3 warnings.")


async def new_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    for member in update.effective_message.new_chat_members:
        if member.is_bot:
            continue
        if is_on(chat.id, "captcha"):
            try:
                await context.bot.restrict_chat_member(chat.id, member.id,
                    ChatPermissions(can_send_messages=False))
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ Verify I'm Human",
                        callback_data=f"verify:{member.id}")
                ]])
                await update.effective_message.reply_text(
                    f"🛡️ {member.mention_html()}, Verify to send messages in this group.",
                    parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                log.warning("Captcha restriction failed: %s", e)
        welcome = get_setting(chat.id, "welcome").replace("{name}", member.first_name)
        await update.effective_message.reply_text(welcome)


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    target_id = int(q.data.split(":")[1])
    if q.from_user.id != target_id:
        await q.answer("This verification button is not for you.", show_alert=True)
        return
    try:
        await context.bot.restrict_chat_member(q.message.chat.id, target_id,
            ChatPermissions(can_send_messages=True, can_send_audios=True,
            can_send_documents=True, can_send_photos=True, can_send_videos=True,
            can_send_video_notes=True, can_send_voice_notes=True,
            can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True))
        await q.answer("Verified!")
        await q.edit_message_text("✅ Verification complete. Welcome!")
    except Exception:
        await q.answer("The bot needs the Restrict Members permission.", show_alert=True)


async def moderate_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not msg or not user or user.is_bot or chat.type == "private":
        return
    if await admin_ok(update):
        return
    text = msg.text or msg.caption or ""

    # Link protection
    if is_on(chat.id, "link_alert") and re.search(r"(https?://|t\.me/|www\.)", text, re.I):
        try:
            await msg.delete()
            await context.bot.send_message(chat.id, "🔗 Sharing links is not allowed.")
        except Exception:
            pass
        return

    # Forward detection
    if is_on(chat.id, "forward_detection") and msg.forward_origin:
        try:
            await msg.delete()
            await context.bot.send_message(chat.id, "⏩ Forwarded messages are disabled.")
        except Exception:
            pass
        return

    # Bad word filter
    words = [w.strip().lower() for w in get_setting(chat.id, "bad_words").split(",") if w.strip()]
    if words and any(w in text.lower() for w in words):
        try:
            await msg.delete()
            if is_on(chat.id, "bad_word_alert"):
                await context.bot.send_message(chat.id, "🤬 Using blocked words is not allowed.")
        except Exception:
            pass
        return

    # Basic anti-spam rate limit
    if is_on(chat.id, "anti_spam"):
        now = datetime.now(timezone.utc).timestamp()
        key = (chat.id, user.id)
        stamps = [t for t in spam_cache.get(key, []) if now - t < int(get_setting(chat.id, "spam_window"))]
        stamps.append(now)
        spam_cache[key] = stamps
        if len(stamps) > int(get_setting(chat.id, "spam_limit")):
            try:
                await context.bot.restrict_chat_member(chat.id, user.id,
                    ChatPermissions(can_send_messages=False), until_date=int(now + 60))
                await context.bot.send_message(chat.id, f"🛡️ {user.mention_html()} temporarily has been muted.",
                                               parse_mode="HTML")
            except Exception:
                pass
            spam_cache[key] = []

    # Keyword auto reply
    for line in get_setting(chat.id, "keywords").splitlines():
        if "=" in line:
            keyword, answer = line.split("=", 1)
            if keyword.strip().lower() in text.lower():
                await msg.reply_text(answer.strip())
                break

    # Custom commands
    for line in get_setting(chat.id, "custom_commands").splitlines():
        if "=" in line:
            command, answer = line.split("=", 1)
            if text.strip().lower() == "/" + command.strip().lower():
                await msg.reply_text(answer.strip())
                break

    reply = get_setting(chat.id, "sms_reply")
    if reply and text:
        await msg.reply_text(reply)


async def my_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = update.my_chat_member
    if member and member.new_chat_member.status in ("member", "administrator"):
        try:
            await context.bot.send_message(member.chat.id,
                "👑 GROUP CONTROLLER has been added!\nGrant admin permissions, then use /panel.")
        except Exception:
            pass


async def post_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.exception("Unhandled bot error", exc_info=context.error)


from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import secrets

WEBHOOK_URL = os.getenv("WEBHOOK_URL", "").strip().rstrip("/")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()

if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")
if not WEBHOOK_URL:
    raise RuntimeError("WEBHOOK_URL is missing. Set it to your deployed Render URL, e.g. https://your-service.onrender.com")
if not WEBHOOK_SECRET or not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", WEBHOOK_SECRET):
    raise RuntimeError("Set WEBHOOK_SECRET to a random 16-256 character value using letters, numbers, _ or -.")

bot_app = Application.builder().token(TOKEN).build()
bot_app.add_handler(CommandHandler("start", start))
bot_app.add_handler(CommandHandler("panel", panel))
bot_app.add_handler(CommandHandler("rules", rules))
bot_app.add_handler(CommandHandler("report", report))
bot_app.add_handler(CommandHandler("id", id_command))
bot_app.add_handler(CommandHandler("clearreply", clearreply))
bot_app.add_handler(CommandHandler("clearpost", clearpost))
for command in ("ban", "mute", "unmute", "warn", "purge"):
    bot_app.add_handler(CommandHandler(command, moderation))
bot_app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))
bot_app.add_handler(CallbackQueryHandler(verify_callback, pattern=r"^verify:"))
bot_app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_members))
bot_app.add_handler(ChatMemberHandler(my_chat_member, ChatMemberHandler.MY_CHAT_MEMBER))
bot_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, receive_setting), group=0)
bot_app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, moderate_messages), group=1)
bot_app.add_error_handler(post_error)

WEBHOOK_PATH = f"/telegram/{WEBHOOK_SECRET}"

@asynccontextmanager
async def lifespan(web_app: FastAPI):
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.bot.set_webhook(
        url=f"{WEBHOOK_URL}{WEBHOOK_PATH}",
        secret_token=WEBHOOK_SECRET,
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=False,
    )
    log.info("GROUP CONTROLLER webhook started at %s", WEBHOOK_URL)
    try:
        yield
    finally:
        try:
            await bot_app.bot.delete_webhook(drop_pending_updates=False)
        except Exception:
            log.exception("Could not delete webhook during shutdown")
        await bot_app.stop()
        await bot_app.shutdown()

web_app = FastAPI(title="GROUP CONTROLLER", lifespan=lifespan)

@web_app.get("/")
async def health():
    return {
        "status": "ok",
        "service": "GROUP CONTROLLER OFFICIAL",
        "mode": "webhook",
    }

@web_app.get("/health")
async def health_check():
    return {"status": "healthy"}

@web_app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    supplied_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not secrets.compare_digest(supplied_secret, WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    try:
        payload = await request.json()
        update = Update.de_json(payload, bot_app.bot)
        await bot_app.update_queue.put(update)
    except Exception:
        log.exception("Invalid Telegram update")
        raise HTTPException(status_code=400, detail="Invalid update")
    return JSONResponse({"ok": True})
