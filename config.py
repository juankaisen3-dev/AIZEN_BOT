import os

from dotenv import load_dotenv

load_dotenv()


def _float_env(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if not raw_value:
        return default

    try:
        return float(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} doit etre un nombre, valeur recue: {raw_value!r}") from exc


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if not raw_value:
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} doit etre un entier, valeur recue: {raw_value!r}") from exc


def _bool_env(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on", "oui"}


def _int_set_env(name: str) -> set[int]:
    raw_value = os.getenv(name, "")
    if not raw_value.strip():
        return set()

    values: set[int] = set()
    for part in raw_value.replace(";", ",").split(","):
        item = part.strip()
        if not item:
            continue
        try:
            values.add(int(item))
        except ValueError as exc:
            raise RuntimeError(
                f"{name} doit contenir des IDs entiers separes par des virgules, "
                f"valeur recue: {raw_value!r}"
            ) from exc
    return values


def _proxy_env() -> str | None:
    proxy_url = (
        os.getenv("TELEGRAM_PROXY_URL")
        or os.getenv("HTTPS_PROXY")
        or os.getenv("HTTP_PROXY")
        or os.getenv("ALL_PROXY")
    )
    if not proxy_url:
        return None

    if "://" not in proxy_url:
        return f"http://{proxy_url}"

    return proxy_url


BOT_TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "downloads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "50"))

BOT_NAME = os.getenv("BOT_NAME", "Aizen")
BOT_CREATOR = os.getenv("BOT_CREATOR", "Oyougou Daniel")
BOT_CREATOR_PSEUDO = os.getenv("BOT_CREATOR_PSEUDO", "Ichigo Kurosaki")
BOT_CREATOR_JOB = os.getenv("BOT_CREATOR_JOB", "Developpeur Full-Stack")
BOT_CREATOR_WHATSAPP = os.getenv("BOT_CREATOR_WHATSAPP", "+24174085772")
BOT_PERSONALITY = os.getenv(
    "BOT_PERSONALITY",
    "sociable, amical, protecteur et passionne d'anime",
)
BOT_OWNER_IDS = _int_set_env("BOT_OWNER_IDS")

raw_stickers = os.getenv("AIZEN_STICKERS", "")
AIZEN_STICKERS = [s.strip() for s in raw_stickers.split(",") if s.strip()]
TELEGRAM_PROXY_URL = _proxy_env()
TELEGRAM_CONNECT_TIMEOUT = _float_env("TELEGRAM_CONNECT_TIMEOUT", 30.0)
TELEGRAM_READ_TIMEOUT = _float_env("TELEGRAM_READ_TIMEOUT", 30.0)
TELEGRAM_WRITE_TIMEOUT = _float_env("TELEGRAM_WRITE_TIMEOUT", 30.0)
TELEGRAM_POOL_TIMEOUT = _float_env("TELEGRAM_POOL_TIMEOUT", 30.0)
TELEGRAM_POLL_TIMEOUT = _int_env("TELEGRAM_POLL_TIMEOUT", 30)
TELEGRAM_BOOTSTRAP_RETRIES = _int_env("TELEGRAM_BOOTSTRAP_RETRIES", 5)
TELEGRAM_RETRY_DELAY = _int_env("TELEGRAM_RETRY_DELAY", 30)
TELEGRAM_REQUIRE_NETWORK_CHECK = _bool_env("TELEGRAM_REQUIRE_NETWORK_CHECK", False)
TELEGRAM_RETRY_WITHOUT_PROXY = _bool_env("TELEGRAM_RETRY_WITHOUT_PROXY", False)


def require_setting(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(
            f"Variable d'environnement manquante: {name}. "
            "Ajoute-la dans le fichier .env avant de lancer le bot."
        )
    return value
