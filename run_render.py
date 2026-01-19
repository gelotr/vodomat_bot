import os
from aiohttp import web

import bot as bot_module

WEBHOOK_PATH = "/telegram"


async def handle(request: web.Request):
    data = await request.json()
    update = bot_module.Update.model_validate(data)
    await bot_module.dp.feed_update(bot_module.bot, update)
    return web.Response(text="ok")


async def on_startup(app: web.Application):
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("WEBHOOK_URL пустой")
    await bot_module.bot.set_webhook(webhook_url, drop_pending_updates=True)


async def on_cleanup(app: web.Application):
    await bot_module.bot.delete_webhook()


def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    port = int(os.environ.get("PORT", "10000"))
    web.run_app(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
