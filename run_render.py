import os
import asyncio
import signal
from aiohttp import web

import bot as bot_module

WEBHOOK_PATH = "/telegram"


async def handle(request: web.Request):
    data = await request.json()
    update = bot_module.Update.model_validate(data)
    await bot_module.dp.feed_update(bot_module.bot, update)
    return web.Response(text="ok")


async def on_startup():
    webhook_url = os.getenv("WEBHOOK_URL", "").strip()
    if not webhook_url:
        raise RuntimeError("WEBHOOK_URL пустой")
    await bot_module.bot.set_webhook(webhook_url, drop_pending_updates=True)


async def shutdown(runner: web.AppRunner):
    await bot_module.bot.delete_webhook()
    await bot_module.bot.session.close()
    await runner.cleanup()


async def main():
    await on_startup()

    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)

    await stop_event.wait()
    await shutdown(runner)


if __name__ == "__main__":
    asyncio.run(main())
