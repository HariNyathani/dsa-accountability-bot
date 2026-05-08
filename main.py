"""
Unified launcher — runs the Discord bot AND FastAPI server concurrently.

Usage:
    python main.py          # both bot + API
    python main.py --api    # API only (no Discord bot)
    python main.py --bot    # bot only  (original behaviour)

The API server runs in a background thread using uvicorn, while the
Discord bot runs on the main asyncio event loop (required by discord.py).
"""

import argparse
import logging
import os
import sys
import threading

import config

# ── Logging (must happen before any module-level loggers) ────────────────────

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("dsa_bot.launcher")


# ── API Server ───────────────────────────────────────────────────────────────

def start_api_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the FastAPI server with uvicorn (blocking)."""
    import uvicorn
    from api.app import create_app

    app = create_app()
    logger.info("Starting API server on %s:%d ...", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


def start_api_thread(host: str = "0.0.0.0", port: int = 8000) -> threading.Thread:
    """Launch the API server in a daemon thread (non-blocking)."""
    t = threading.Thread(
        target=start_api_server,
        args=(host, port),
        name="api-server",
        daemon=True,
    )
    t.start()
    logger.info("API server thread started (port %d).", port)
    return t


# -- Discord Bot --------------------------------------------------------------

def start_bot() -> None:
    """Import and run the Discord bot (blocks on bot.run)."""
    # Defer import so bot.py module-level code only runs when needed
    from bot import main as bot_main
    bot_main()


# ── Entry Point ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="DSA Accountability Bot Launcher")
    parser.add_argument("--api", action="store_true", help="Run API server only")
    parser.add_argument("--bot", action="store_true", help="Run Discord bot only")
    parser.add_argument("--port", type=int, default=int(os.getenv("API_PORT", "8000")),
                        help="API server port (default: 8000)")
    parser.add_argument("--host", type=str, default=os.getenv("API_HOST", "0.0.0.0"),
                        help="API server host (default: 0.0.0.0)")
    args = parser.parse_args()

    if args.api:
        # API-only mode
        logger.info("Launching in API-only mode.")
        start_api_server(args.host, args.port)

    elif args.bot:
        # Bot-only mode (original behaviour)
        logger.info("Launching in bot-only mode.")
        start_bot()

    else:
        # Default: both
        logger.info("Launching bot + API concurrently.")
        start_api_thread(args.host, args.port)
        start_bot()  # blocks here


if __name__ == "__main__":
    main()
