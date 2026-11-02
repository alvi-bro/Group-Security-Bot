# GROUP CONTROLLER OFFICIAL — English Premium Webhook Edition

Deploy as a Render **Web Service** (not Background Worker).

Build command: `pip install -r requirements.txt`

Start command: `uvicorn main:web_app --host 0.0.0.0 --port $PORT`

Environment Variables:
- `BOT_TOKEN`: Telegram bot token from @BotFather
- `OWNER_ID`: Numeric Telegram user ID (optional; use 0 if not used)
- `WEBHOOK_SECRET`: 16–256 characters using letters, numbers, underscore, or hyphen
- `DB_PATH`: `group_controller.db`

On Render, `WEBHOOK_URL` is automatically read from `RENDER_EXTERNAL_URL`. You may set `WEBHOOK_URL` manually if needed.

Interface messages and inline button labels use English text with the requested Mathematical Bold Unicode style. Telegram commands and text inside `<code>` tags remain plain ASCII so they continue to work. Custom messages entered by group admins are kept as entered rather than automatically translated.
