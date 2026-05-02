import logging
import socket
import time
from urllib.parse import urlparse

from telegram import BotCommand, Update
from telegram.error import NetworkError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    TELEGRAM_BOOTSTRAP_RETRIES,
    TELEGRAM_CONNECT_TIMEOUT,
    TELEGRAM_POLL_TIMEOUT,
    TELEGRAM_POOL_TIMEOUT,
    TELEGRAM_PROXY_URL,
    TELEGRAM_READ_TIMEOUT,
    TELEGRAM_REQUIRE_NETWORK_CHECK,
    TELEGRAM_RETRY_DELAY,
    TELEGRAM_RETRY_WITHOUT_PROXY,
    TELEGRAM_WRITE_TIMEOUT,
    require_setting,
)
from database.cache import init_db
from handlers.anime_search import random_anime, search_anime, top_anime
from handlers.gemini_ai import ask_ai, clear_conversation
from handlers.personal import (
    admin_command,
    broadcast_command,
    callback_handler,
    chatid_command,
    conversation_handler,
    creator_command,
    help_command as personal_help_command,
    info_command,
    joke_command,
    love_command,
    menu_command,
    ping_command,
    quote_command,
    start_command,
    stats_command,
    surprise_command,
    time_command,
    track_activity,
    handle_sticker,
)
from handlers.youtube_dl import download_amv, download_ed, download_link, download_op, download_any, download_song, generate_image_cmd
from handlers.advanced import (
    fav_command,
    unfav_command,
    mesfavs_command,
    note_command,
    montop_command,
    rappel_command,
    check_reminders,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PROXY_DEFAULT_PORTS = {
    "http": 8080,
    "https": 8080,
    "socks4": 1080,
    "socks5": 1080,
}

COMMANDS = [
    ("start", "Ouvrir l'accueil"),
    ("menu", "Menu interactif"),
    ("aide", "Afficher l'aide"),
    ("help", "Afficher l'aide"),
    ("recherche", "Rechercher un anime par nom"),
    ("random", "Anime aleatoire"),
    ("top", "Top animes du moment"),
    ("op", "Telecharger un opening"),
    ("ed", "Telecharger un ending"),
    ("amv", "Telecharger un AMV"),
    ("n", "Rechercher films, series, episodes"),
    ("dl", "Telecharger via lien (TikTok, YT)"),
    ("ia", "Poser une question a l'IA"),
    ("clear", "Effacer l'historique IA"),
    ("info", "Informations du bot"),
    ("creator", "Informations createur"),
    ("ping", "Verifier l'etat du bot"),
    ("time", "Date et heure"),
    ("chatid", "Afficher ton ID"),
    ("love", "Message personnel"),
    ("joke", "Blague"),
    ("quote", "Citation"),
    ("surprise", "Surprise"),
    ("admin", "Espace createur"),
    ("stats", "Statistiques"),
    ("broadcast", "Message global"),
]


async def post_init(app: Application) -> None:
    commands = [BotCommand(command, description) for command, description in COMMANDS]
    await app.bot.set_my_commands(commands)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Erreur non geree: %s", context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Une erreur est survenue. Reessaie plus tard.")


def build_application(token: str) -> Application:
    builder = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .connect_timeout(TELEGRAM_CONNECT_TIMEOUT)
        .read_timeout(TELEGRAM_READ_TIMEOUT)
        .write_timeout(TELEGRAM_WRITE_TIMEOUT)
        .pool_timeout(TELEGRAM_POOL_TIMEOUT)
        .get_updates_connect_timeout(TELEGRAM_CONNECT_TIMEOUT)
        .get_updates_read_timeout(TELEGRAM_READ_TIMEOUT)
        .get_updates_write_timeout(TELEGRAM_WRITE_TIMEOUT)
        .get_updates_pool_timeout(TELEGRAM_POOL_TIMEOUT)
    )

    if TELEGRAM_PROXY_URL:
        builder = builder.proxy(TELEGRAM_PROXY_URL).get_updates_proxy(TELEGRAM_PROXY_URL)

    return builder.build()


def proxy_endpoint(proxy_url: str) -> tuple[str, int, str]:
    parsed = urlparse(proxy_url)
    if not parsed.scheme or not parsed.hostname:
        raise RuntimeError(
            "TELEGRAM_PROXY_URL est invalide. Exemple valide: "
            "http://127.0.0.1:7890 ou socks5://127.0.0.1:10808"
        )

    if parsed.scheme not in PROXY_DEFAULT_PORTS:
        raise RuntimeError(
            f"Schema de proxy non supporte: {parsed.scheme!r}. "
            "Utilise http://, https://, socks4:// ou socks5://."
        )

    port = parsed.port or PROXY_DEFAULT_PORTS[parsed.scheme]
    return parsed.hostname, port, parsed.scheme


def ensure_telegram_api_reachable() -> bool:
    if TELEGRAM_PROXY_URL:
        try:
            host, port, scheme = proxy_endpoint(TELEGRAM_PROXY_URL)
            with socket.create_connection((host, port), timeout=TELEGRAM_CONNECT_TIMEOUT):
                return True
        except (RuntimeError, ValueError) as exc:
            logger.error("%s", exc)
            return False
        except OSError as exc:
            logger.error(
                "Le proxy Telegram est configure (%s://%s:%s), mais il est inaccessible: %s. "
                "Lance ton VPN/proxy local, verifie le port, ou corrige TELEGRAM_PROXY_URL dans .env.",
                scheme,
                host,
                port,
                exc,
            )
            return False

    try:
        with socket.create_connection(("api.telegram.org", 443), timeout=TELEGRAM_CONNECT_TIMEOUT):
            return True
    except OSError as exc:
        logger.error(
            "Impossible de se connecter a api.telegram.org:443: %s. "
            "Telegram est probablement bloque par le reseau, le pare-feu, le VPN ou le FAI. "
            "Essaie un autre reseau ou ajoute TELEGRAM_PROXY_URL dans .env.",
            exc,
        )
        return False


def telegram_network_help() -> str:
    return (
        "Correction necessaire: Telegram est bloque sur ce reseau et aucun proxy n'est configure.\n\n"
        "1. Lance un VPN, ou une application proxy comme Clash, V2Ray, NekoRay, Hiddify, Shadowsocks, Tor, etc.\n"
        "2. Recupere son adresse locale, puis ajoute UNE de ces lignes dans .env:\n"
        "   TELEGRAM_PROXY_URL=http://127.0.0.1:7890\n"
        "   TELEGRAM_PROXY_URL=socks5://127.0.0.1:10808\n"
        "   TELEGRAM_PROXY_URL=socks5://127.0.0.1:9050\n\n"
        "Ports frequents: 7890 pour Clash, 10808 pour V2Ray/NekoRay, 9050 pour Tor.\n"
        "Si tu utilises un VPN complet, active-le puis relance python bot.py."
    )


def main():
    init_db()

    token = require_setting(BOT_TOKEN, "BOT_TOKEN")

    print("Verification de la connexion a Telegram en cours...")
    while True:
        if not ensure_telegram_api_reachable():
            if not TELEGRAM_PROXY_URL and not TELEGRAM_RETRY_WITHOUT_PROXY:
                logger.error(telegram_network_help())
                raise SystemExit(1)

            if TELEGRAM_REQUIRE_NETWORK_CHECK:
                raise SystemExit(1)

            logger.warning(
                "Demarrage reporte: Telegram est inaccessible pour le moment. "
                "Nouvelle tentative dans %s secondes.",
                TELEGRAM_RETRY_DELAY,
            )
            time.sleep(TELEGRAM_RETRY_DELAY)
            continue

        app = build_application(token)
        register_handlers(app)

        print("Aizen_bot demarre...")
        try:
            app.run_polling(
                allowed_updates=Update.ALL_TYPES,
                bootstrap_retries=TELEGRAM_BOOTSTRAP_RETRIES,
                timeout=TELEGRAM_POLL_TIMEOUT,
            )
            break
        except NetworkError as exc:
            logger.error(
                "Impossible de joindre l'API Telegram: %s. "
                "Nouvelle tentative dans %s secondes. "
                "Si cela continue, configure TELEGRAM_PROXY_URL dans .env.",
                exc,
                TELEGRAM_RETRY_DELAY,
            )
            time.sleep(TELEGRAM_RETRY_DELAY)


def register_handlers(app: Application) -> None:
    app.add_handler(MessageHandler(filters.ALL, track_activity), group=-1)

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler(["aide", "help"], personal_help_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("recherche", search_anime))
    app.add_handler(CommandHandler("random", random_anime))
    app.add_handler(CommandHandler("top", top_anime))
    app.add_handler(CommandHandler("op", download_op))
    app.add_handler(CommandHandler("ed", download_ed))
    app.add_handler(CommandHandler("amv", download_amv))
    app.add_handler(CommandHandler("n", download_any))
    app.add_handler(CommandHandler("dl", download_link))
    app.add_handler(CommandHandler("ia", ask_ai))
    app.add_handler(CommandHandler("clear", clear_conversation))
    app.add_handler(CommandHandler("info", info_command))
    app.add_handler(CommandHandler("creator", creator_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("time", time_command))
    app.add_handler(CommandHandler("chatid", chatid_command))
    app.add_handler(CommandHandler("love", love_command))
    app.add_handler(CommandHandler("joke", joke_command))
    app.add_handler(CommandHandler("quote", quote_command))
    app.add_handler(CommandHandler("surprise", surprise_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("song", download_song))
    app.add_handler(CommandHandler("img", generate_image_cmd))

    # Features avancees
    app.add_handler(CommandHandler("fav", fav_command))
    app.add_handler(CommandHandler("unfav", unfav_command))
    app.add_handler(CommandHandler("mesfavs", mesfavs_command))
    app.add_handler(CommandHandler("note", note_command))
    app.add_handler(CommandHandler("montop", montop_command))
    app.add_handler(CommandHandler("rappel", rappel_command))

    # Rappels automatiques
    if app.job_queue:
        app.job_queue.run_repeating(check_reminders, interval=60, first=10)

    app.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, conversation_handler))
    app.add_error_handler(error_handler)


if __name__ == "__main__":
    main()
