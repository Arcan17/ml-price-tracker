import logging
import os
import threading

import uvicorn
from dotenv import load_dotenv

load_dotenv()

from api.main import app as health_app  # noqa: E402
from bot.handlers import build_application  # noqa: E402
from models.database import init_db  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def _run_health_server() -> None:
    uvicorn.run(health_app, host="0.0.0.0", port=8080, log_level="warning")


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and add your token."
        )

    init_db()
    logger.info("Database initialized")

    threading.Thread(target=_run_health_server, daemon=True).start()
    logger.info("Health server listening on :8080")

    application = build_application(token)
    logger.info("Bot starting — polling for updates…")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
