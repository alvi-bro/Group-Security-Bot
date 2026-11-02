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

DEFAULTS = {
    "welcome": "👋 স্বাগতম {name}!\nআমাদের গ্রুপে যোগ দেওয়ার জন্য ধন্যবাদ।",
    "rules": "📜 গ্রুপের নিয়মাবলি:\n1. সবাইকে সম্মান করুন\n2. স্প্যাম করবেন না\n3. অপ্রাসঙ্গিক লিংক শেয়ার করবেন না",
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
        "নিচের বাটন থেকে প্রয়োজনীয় সেটিংস নির্বাচন করো।"
    )
    await message.reply_text(title, reply_markup=main_keyboard(), parse_mode="HTML")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👑 <b>GROUP CONTROLLER OFFICIAL</b>\n\n"
        "আমি তোমার গ্রুপ পরিচালনা ও মডারেশনে সাহায্য করতে পারি।\n\n"
        "1️⃣ আমাকে গ্রুপে Add করো\n"
        "2️⃣ প্রয়োজনীয় Admin Permission দাও\n"
        "3️⃣ গ্রুপে /panel লিখে কন্ট্রোল প্যানেল খোলো"
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
            "কন্ট্রোল প্যানেল খুলতে বটকে গ্রুপে Add করে সেই গ্রুপে /panel লিখো।"
        )
        return
    if not await admin_ok(update):
        await update.effective_message.reply_text("⛔ শুধু গ্রুপ Admin এই প্যানেল ব্যবহার করতে পারবেন।")
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
            await q.answer("শুধু গ্রুপ Admin ব্যবহার করতে পারবেন।", show_alert=True)
            return
        await q.edit_message_text(
            "👑 <b>GROUP CONTROLLER OFFICIAL</b>\n━━━━━━━━━━━━━━━━━━━━\n"
            "⚙️ Premium Group Control Panel\n\nএকটি সেটিংস নির্বাচন করো।",
            parse_mode="HTML", reply_markup=main_keyboard())
        return

    if data in ("help", "about", "add", "mods"):
        pages = {
            "help": "📚 <b>HELP CENTER</b>\n\n/panel — Control Panel\n/rules — গ্রুপের নিয়ম\n/report — Admin-কে রিপোর্ট\n/id — Chat ও User ID\n\nমডারেশন: /ban, /mute, /unmute, /warn, /purge\n\nবটকে প্রয়োজনীয় Admin Permission দিতে হবে।",
            "about": "🤖 <b>GROUP CONTROLLER</b>\n\nPremium Telegram Group Management Bot.\nRender ও GitHub-এ হোস্ট করার জন্য প্রস্তুত।",
            "add": "👥 <b>ADD GROUP</b>\n\nবটকে গ্রুপে যোগ করো, তারপর Admin Permission দিয়ে /panel চালাও।",
            "mods": "🛡️ <b>MOD COMMANDS</b>\n\nরিপ্লাই করে ব্যবহার করো:\n/ban — সদস্য Ban\n/mute — সদস্য Mute\n/unmute — Mute তুলে দেওয়া\n/warn — Warning\n/purge — রিপ্লাই থেকে বর্তমান মেসেজ পর্যন্ত মুছবে"
        }
        await q.edit_message_text(pages[data], parse_mode="HTML", reply_markup=back_keyboard())
        return

    if not await admin_ok(update, chat_id):
        await q.answer("⛔ শুধু গ্রুপ Admin এই সেটিংস পরিবর্তন করতে পারবেন।", show_alert=True)
        return

    toggles = {
        "link_alert": ("🔗 Link Alert", "লিংকযুক্ত মেসেজ মুছে সতর্ক করবে।"),
        "anti_spam": ("🛡️ Anti Spam", "দ্রুত অনেক মেসেজ পাঠালে সীমাবদ্ধ করবে।"),
        "bad_word_alert": ("🤬 Bad Word Alert", "নিষিদ্ধ শব্দ পেলে সতর্ক করবে।"),
        "night_mode": ("🌙 Night Mode", "রাত ১২টা–সকাল ৬টায় সাধারণ সদস্যদের মেসেজ সীমিত করবে না; এটি শুধু সেটিংস ফ্ল্যাগ।"),
        "force_subscribe": ("📢 Force Subscribe", "নির্দিষ্ট চ্যানেল সাবস্ক্রিপশন চেক করবে।"),
        "report_system": ("🚨 Report System", "সদস্যদের /report চালু বা বন্ধ করবে।"),
        "language_filter": ("🌐 Language Filter", "নির্বাচিত ভাষার ফিল্টার শব্দ কনফিগার করতে হবে।"),
        "forward_detection": ("⏩ Forward Detection", "Forward করা মেসেজ শনাক্ত করে সতর্ক করবে।"),
        "captcha": ("🛡️ Captcha System", "নতুন সদস্যকে Verify বাটন দেখাবে।"),
        "bot_msg_remove": ("🤖 Bot Msg Remove", "বটের পাঠানো সার্ভিস মেসেজ পরিষ্কারের অপশন।")
    }
    if data in toggles:
        title, desc = toggles[data]
        new = "0" if is_on(chat_id, data) else "1"
        set_setting(chat_id, data, new)
        state = "ON ✅" if new == "1" else "OFF ❌"
        await q.edit_message_text(
            f"<b>{title}</b>\n\n{desc}\n\nবর্তমান অবস্থা: <b>{state}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Toggle", callback_data=f"menu:{data}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="menu:home")]
            ]))
        return

    prompts = {
        "welcome": ("👋 Welcome Message", "নতুন সদস্যের জন্য Welcome Message পাঠাও। {name} ব্যবহার করলে সদস্যের নাম বসবে।"),
        "rules": ("📜 Group Rules", "গ্রুপের নিয়মাবলি পাঠাও।"),
        "bad_words": ("🤬 Bad Words", "নিষিদ্ধ শব্দগুলো কমা দিয়ে পাঠাও। যেমন: word1, word2"),
        "keywords": ("💬 Keyword Auto Reply", "কীওয়ার্ড ও উত্তর এভাবে পাঠাও:\nhello = Hello!\nprice = Please contact admin"),
        "custom_commands": ("💻 Custom Commands", "কাস্টম কমান্ড এভাবে পাঠাও:\nstartinfo = Welcome to our group\nhelpdesk = Contact admin"),
        "sms_reply": ("✉️ SMS Reply", "সাধারণ Auto Reply টেক্সট পাঠাও। বন্ধ করতে /clearreply লিখো।"),
        "auto_post": ("📣 Auto Post", "Auto Post সেট করতে পোস্টের টেক্সট পাঠাও। বন্ধ করতে /clearpost লিখো।"),
        "loop_post": ("📅 Loop Post", "Loop Post-এর টেক্সট পাঠাও। বর্তমানে এটি সংরক্ষণ করবে; নির্দিষ্ট সময়সূচি সেট করতে Render-এ Job Queue চালু থাকতে হবে।"),
        "force_subscribe": ("📢 Force Subscribe Channel", "চ্যানেল ইউজারনেম পাঠাও, যেমন @mychannel। চ্যানেলটি Public হতে হবে এবং বটকে সেখানে যুক্ত করতে হবে।")
    }
    if data in prompts:
        title, desc = prompts[data]
        pending[(chat_id, user_id)] = data
        await q.edit_message_text(
            f"<b>{title}</b>\n\n{desc}\n\n"
            "এখন গ্রুপে পরের মেসেজটি পাঠাও।",
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
            await msg.reply_text("চ্যানেল username @ দিয়ে পাঠাও।")
            return
        set_setting(chat.id, "required_channel", value)
        set_setting(chat.id, key, "1")
    else:
        set_setting(chat.id, key, value)
    pending.pop((chat.id, user.id), None)
    await msg.reply_text(f"✅ <b>{key.replace('_',' ').title()}</b> সংরক্ষণ করা হয়েছে।",
                         parse_mode="HTML", reply_markup=main_keyboard())


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.effective_message.reply_text(get_setting(chat_id, "rules"))


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not is_on(chat.id, "report_system"):
        return
    if not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("যে মেসেজটি রিপোর্ট করতে চাও সেটিতে Reply করে /report লেখো।")
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
    await update.effective_message.reply_text("✅ রিপোর্ট Admin-দের পাঠানো হয়েছে।")


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
    await update.effective_message.reply_text("✅ সেটিংস ক্লিয়ার করা হয়েছে।")


async def clearreply(update, context):
    await clear_setting(update, context, "sms_reply")


async def clearpost(update, context):
    await clear_setting(update, context, "auto_post")


async def moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat = update.effective_chat
    cmd = msg.text.split()[0].split("@")[0].lower()
    if not await admin_ok(update):
        await msg.reply_text("⛔ শুধু Admin এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if cmd == "/purge":
        if not msg.reply_to_message:
            await msg.reply_text("যে মেসেজ থেকে মুছবে সেটিতে Reply করে /purge দাও।")
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
        await msg.reply_text("কোনো সদস্যের মেসেজে Reply করে এই কমান্ড দাও।")
        return
    if cmd == "/ban":
        await context.bot.ban_chat_member(chat.id, target.id)
        await msg.reply_text(f"⛔ {target.first_name} Ban করা হয়েছে।")
    elif cmd == "/mute":
        await context.bot.restrict_chat_member(chat.id, target.id,
            ChatPermissions(can_send_messages=False))
        await msg.reply_text(f"🔇 {target.first_name} Mute করা হয়েছে।")
    elif cmd == "/unmute":
        await context.bot.restrict_chat_member(chat.id, target.id,
            ChatPermissions(can_send_messages=True, can_send_audios=True,
            can_send_documents=True, can_send_photos=True, can_send_videos=True,
            can_send_video_notes=True, can_send_voice_notes=True,
            can_send_polls=True, can_send_other_messages=True,
            can_add_web_page_previews=True))
        await msg.reply_text(f"🔊 {target.first_name} Unmute করা হয়েছে।")
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
            await msg.reply_text("⛔ ৩টি Warning হওয়ায় সদস্য Ban হয়েছে।")


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
                    f"🛡️ {member.mention_html()}, গ্রুপে লিখতে Verify করো।",
                    parse_mode="HTML", reply_markup=kb)
            except Exception as e:
                log.warning("Captcha restriction failed: %s", e)
        welcome = get_setting(chat.id, "welcome").replace("{name}", member.first_name)
        await update.effective_message.reply_text(welcome)


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    target_id = int(q.data.split(":")[1])
    if q.from_user.id != target_id:
        await q.answer("এই Verify বাটনটি তোমার জন্য নয়।", show_alert=True)
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
        await q.answer("বটের Restrict Members permission প্রয়োজন।", show_alert=True)


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
            await context.bot.send_message(chat.id, "🔗 লিংক শেয়ার করা অনুমোদিত নয়।")
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
                await context.bot.send_message(chat.id, "🤬 নিষিদ্ধ শব্দ ব্যবহার করা যাবে না।")
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
                await context.bot.send_message(chat.id, f"🛡️ {user.mention_html()} সাময়িকভাবে Mute করা হয়েছে।",
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
                "👑 GROUP CONTROLLER যুক্ত হয়েছে!\nAdmin Permission দিয়ে /panel চালু করো।")
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
