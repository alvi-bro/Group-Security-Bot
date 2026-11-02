# GROUP CONTROLLER OFFICIAL — Render Free Webhook Edition

Telegram group management bot with a colorful two-column inline control panel.

## Deploy on Render Free
This version uses a **Webhook + FastAPI** server, not long polling. Deploy it as a Render **Web Service** (not Background Worker).

1. Create a bot with @BotFather and copy its token.
2. Upload this project to GitHub.
3. In Render, choose **New → Web Service** and connect the repository.
4. Use:
   - Runtime: Python
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn main:web_app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `BOT_TOKEN`: token from BotFather
   - `OWNER_ID`: your Telegram numeric user ID (optional)
   - `WEBHOOK_URL`: your Render service URL, e.g. `https://group-controller-bot.onrender.com` (no trailing slash)
   - `WEBHOOK_SECRET`: random 16–256 characters using only A-Z, a-z, 0-9, `_` or `-`
   - `DB_PATH`: `group_controller.db`
6. Deploy. Open `https://YOUR-SERVICE.onrender.com/health`; it should return `{"status":"healthy"}`.
7. Add the bot to your group, promote it to admin with required permissions, then send `/panel`.

## Features in this starter
- Two-column inline control panel
- Welcome and rules configuration
- Link filter, bad-word filter, basic anti-spam and forward detection
- Keyword auto-reply and custom command replies
- Report system and captcha-style join verification
- Admin commands: `/ban`, `/mute`, `/unmute`, `/warn`, `/purge`

## Free hosting limitations
- Render Free Web Services can sleep after inactivity and may take time to wake. A sleeping service is not guaranteed to respond instantly to Telegram updates.
- The free filesystem is ephemeral. SQLite data may be lost on redeploy, restart, or instance replacement. Use an external persistent database for durable production settings.
- Free service availability and quotas are controlled by Render and can change.
- The bot needs Telegram admin permissions for moderation, deleting messages, and member restrictions.
- Some menu items are starter/configuration sections, not fully automated production features yet (for example scheduled Auto Post/Loop Post, full Force Subscribe enforcement, and advanced language filtering).
- Admins must have opened the bot privately before Telegram can deliver private report messages to them.
- Never commit your bot token or webhook secret to GitHub. Set them only in Render Environment Variables.
