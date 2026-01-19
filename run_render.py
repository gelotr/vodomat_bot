import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# маленький HTTP endpoint, чтобы Render видел открытый порт
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

def run_http():
    port = int(os.environ.get("PORT", "10000"))
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()

def run_bot():
    import bot
    import asyncio
    asyncio.run(bot.main())

if __name__ == "__main__":
    threading.Thread(target=run_http, daemon=True).start()
    run_bot()
