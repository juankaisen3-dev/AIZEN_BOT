import random
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import (
    BOT_CREATOR,
    BOT_CREATOR_JOB,
    BOT_CREATOR_PSEUDO,
    BOT_CREATOR_WHATSAPP,
    BOT_NAME,
    BOT_OWNER_IDS,
    BOT_PERSONALITY,
)
from database.cache import (
    get_bot_stats,
    get_recent_users,
    list_user_chat_ids,
    track_user,
)
from handlers.anime_search import format_anime_result
from services.jikan_client import get_random_anime_api, get_top_anime_api


LOVE_MESSAGES = [
    "Tu es le createur qui donne de la lumiere a mon code.",
    "Chaque commande que tu m'envoies me rend un peu plus utile.",
    "Je garde toujours une reponse douce pour mon Shinigami.",
    "Ton idee, mon execution: l'equipe parfaite.",
]

JOKES = [
    "Pourquoi Aizen adore les animes ? Parce que chaque arc cache un bon plan.",
    "Un bot entre dans un dojo Python. Il ressort avec une indentation parfaite.",
    "Mon super-pouvoir ? Repondre vite, sauf quand YouTube decide de faire durer le suspense.",
    "Je voulais devenir Hokage, puis j'ai vu la file d'attente des updates Telegram.",
]

QUOTES = [
    "Un bon plan commence toujours par une bonne commande.",
    "La puissance sans style, c'est juste une boucle while mal assumee.",
    "Chaque recherche d'anime est une porte vers un nouvel univers.",
    "Le code obeit mieux quand il respecte son createur.",
]

SURPRISES = [
    "Surprise: aujourd'hui, ton assistant est pret a chercher, conseiller et telecharger sans faire le difficile.",
    "Petit cadeau: /random peut te sortir une pepite anime quand tu ne sais plus quoi regarder.",
    "Mode Shinigami active: calme, precision, et menus bien ranges.",
    "Je n'ai pas de zanpakuto, mais j'ai des callbacks Telegram. C'est deja dangereux.",
]


def is_owner(user_id: int | None) -> bool:
    return bool(user_id and user_id in BOT_OWNER_IDS)


def _owner_required_text() -> str:
    if not BOT_OWNER_IDS:
        return (
            "Espace createur non configure.\n\n"
            "Ajoute ton ID Telegram dans BOT_OWNER_IDS dans .env, puis utilise /chatid "
            "pour verifier la bonne valeur."
        )

    return "Acces reserve au createur du bot."


def _main_menu_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Anime", callback_data="category_anime"),
                InlineKeyboardButton("Telechargements", callback_data="category_downloads"),
            ],
            [
                InlineKeyboardButton("IA", callback_data="category_ai"),
                InlineKeyboardButton("Fun", callback_data="category_fun"),
            ],
            [
                InlineKeyboardButton("Outils", callback_data="category_tools"),
                InlineKeyboardButton("Createur", callback_data="category_owner"),
            ],
            [InlineKeyboardButton("Aide", callback_data="category_help")],
        ]
    )


def _back_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Retour menu", callback_data="menu_main")]])


def _anime_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Anime aleatoire", callback_data="cmd_random"),
                InlineKeyboardButton("Top 5", callback_data="cmd_top"),
            ],
            [InlineKeyboardButton("Retour menu", callback_data="menu_main")],
        ]
    )


def _fun_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Message", callback_data="fun_love"),
                InlineKeyboardButton("Blague", callback_data="fun_joke"),
            ],
            [
                InlineKeyboardButton("Citation", callback_data="fun_quote"),
                InlineKeyboardButton("Surprise", callback_data="fun_surprise"),
            ],
            [InlineKeyboardButton("Retour menu", callback_data="menu_main")],
        ]
    )


def _tools_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Ping", callback_data="cmd_ping"),
                InlineKeyboardButton("Heure", callback_data="cmd_time"),
            ],
            [
                InlineKeyboardButton("Infos", callback_data="cmd_info"),
                InlineKeyboardButton("Mon ID", callback_data="cmd_chatid"),
            ],
            [InlineKeyboardButton("Retour menu", callback_data="menu_main")],
        ]
    )


def _owner_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("Statistiques", callback_data="admin_stats")],
            [InlineKeyboardButton("Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("Retour menu", callback_data="menu_main")],
        ]
    )


async def _edit_or_reply(update: Update, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    query = update.callback_query
    if query:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup)
            return
        except Exception:
            if query.message:
                await query.message.reply_text(text, reply_markup=reply_markup)
                return

    if update.effective_message:
        await update.effective_message.reply_text(text, reply_markup=reply_markup)


async def remember_user(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback: bool = False) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    track_user(
        user_id=user.id,
        chat_id=chat.id,
        first_name=user.first_name or "",
        username=user.username or "",
        is_callback=is_callback,
    )


async def track_activity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await remember_user(update, context, is_callback=False)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import os
    user = update.effective_user
    first_name = user.first_name if user and user.first_name else "toi"

    caption = (
        f"Yo {first_name} 👋🔥\n\n"
        f"C'est moi, *{BOT_NAME}* — ton pote anime, IA et telechargements.\n"
        f"Cree par *{BOT_CREATOR}* aka *{BOT_CREATOR_PSEUDO}* ⚔️\n\n"
        "Voila ce que je sais faire :\n"
        "🎬 `/dl` — Telecharger TikTok/YouTube\n"
        "🎵 `/song` — Chanson en MP3\n"
        "🖼️ `/img` — Generer une image\n"
        "🔍 `/n` — Chercher un anime/film/serie\n"
        "🎞️ `/op /ed /amv` — Openings, Endings, AMVs\n"
        "💬 Parle-moi directement aussi, je reponds !\n\n"
        "Sdk bro, je suis la pour toi 😎"
    )

    banner_path = os.path.join(os.path.dirname(__file__), "..", "assets", "aizen_banner.png")
    banner_path = os.path.abspath(banner_path)

    try:
        if os.path.exists(banner_path):
            with open(banner_path, "rb") as img:
                await update.effective_message.reply_photo(
                    photo=img,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_markup=_main_menu_markup(),
                )
        else:
            raise FileNotFoundError
    except Exception:
        # Fallback texte si l'image est absente
        await update.effective_message.reply_text(
            caption,
            parse_mode="Markdown",
            reply_markup=_main_menu_markup(),
        )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        f"Menu principal de {BOT_NAME}.",
        reply_markup=_main_menu_markup(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"Guide rapide - {BOT_NAME}\n\n"
        "Anime:\n"
        "/recherche <nom> - chercher un anime\n"
        "/random - anime aleatoire\n"
        "/top - top animes du moment\n\n"
        "Telechargements:\n"
        "/n <nom> - rechercher episode, film ou serie\n"
        "/dl <lien> - telecharger lien TikTok/YouTube\n"
        "/song <titre> - telecharger une chanson en MP3\n"
        "/op <anime> - trouver un opening\n"
        "/ed <anime> - trouver un ending\n"
        "/amv <anime> - trouver un AMV\n\n"
        "Images:\n"
        "/img <description> - generer une image avec l'IA\n\n"
        "Favoris & Top :\n"
        "/fav <anime> [note] - ajouter un favori\n"
        "/note <anime> <1-10> - noter un anime\n"
        "/montop - voir ton classement perso\n"
        "/mesfavs - voir tous tes favoris\n\n"
        "Outils :\n"
        "/rappel <duree> <texte> - creer un rappel (ex: 20min)\n"
        "/ia <question> - parler avec l'IA\n"
        "/clear - effacer ton historique IA\n"
        "/menu - ouvrir le menu interactif\n"
        "/info - infos du bot\n"
        "/creator - infos createur\n"
        "/ping - verifier le bot\n"
        "/time - date et heure\n"
        "/chatid - afficher ton ID Telegram\n\n"
        "Fun:\n"
        "/love, /joke, /quote, /surprise\n\n"
        "Createur:\n"
        "/admin, /stats, /broadcast <message>"
    )
    await update.effective_message.reply_text(text, reply_markup=_main_menu_markup())


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    stats = get_bot_stats()
    text = (
        f"Informations - {BOT_NAME}\n\n"
        f"Nom: {BOT_NAME}\n"
        f"Createur: {BOT_CREATOR} ({BOT_CREATOR_PSEUDO})\n"
        f"Personnalite: {BOT_PERSONALITY}\n"
        "Langage: Python\n"
        "Specialite: anime, IA, openings, endings et AMV\n\n"
        "Activite:\n"
        f"Utilisateurs connus: {stats['users_total']}\n"
        f"Messages recus: {stats['messages_total']}\n"
        f"Interactions menu: {stats['callbacks_total']}"
    )
    await update.effective_message.reply_text(text, reply_markup=_back_markup())


async def creator_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    import os
    caption = (
        "⚔️ *Createur du bot*\n\n"
        f"👤 *Nom:* {BOT_CREATOR}\n"
        f"🎭 *Pseudo:* {BOT_CREATOR_PSEUDO}\n"
        f"💼 *Metier:* {BOT_CREATOR_JOB}\n"
        f"📱 *WhatsApp:* {BOT_CREATOR_WHATSAPP}\n\n"
        f"_{BOT_NAME} a ete cree par ce guerrier avec passion et expertise._ 🔥"
    )

    banner_path = os.path.join(os.path.dirname(__file__), "..", "assets", "creator_banner.jpg")
    banner_path = os.path.abspath(banner_path)

    try:
        if os.path.exists(banner_path):
            with open(banner_path, "rb") as img:
                await update.effective_message.reply_photo(
                    photo=img,
                    caption=caption,
                    parse_mode="Markdown",
                )
        else:
            raise FileNotFoundError
    except Exception:
        await update.effective_message.reply_text(
            caption,
            parse_mode="Markdown",
        )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text("Pong. Aizen est operationnel.")


async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    now = datetime.now().astimezone()
    text = (
        "Date et heure\n\n"
        f"Date: {now.strftime('%d/%m/%Y')}\n"
        f"Heure: {now.strftime('%H:%M:%S')}\n"
        f"Fuseau: {now.tzname() or 'local'}"
    )
    await update.effective_message.reply_text(text)


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user
    if not chat or not user:
        return

    await update.effective_message.reply_text(
        f"Tes identifiants\n\nChat ID: {chat.id}\nUser ID: {user.id}"
    )


async def love_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(random.choice(LOVE_MESSAGES))


async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(random.choice(JOKES))


async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(f"Citation\n\n{random.choice(QUOTES)}")


async def surprise_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(random.choice(SURPRISES))


def _stats_text() -> str:
    stats = get_bot_stats()
    recent_users = get_recent_users(limit=5)
    lines = [
        "Statistiques detaillees",
        "",
        f"Utilisateurs: {stats['users_total']}",
        f"Messages: {stats['messages_total']}",
        f"Interactions menu: {stats['callbacks_total']}",
        f"Echanges IA: {stats['conversations_total']}",
        f"Telechargements: {stats['downloads_success']}/{stats['downloads_total']} reussis",
        "",
        "Derniers utilisateurs:",
    ]

    if not recent_users:
        lines.append("Aucun utilisateur enregistre.")
    else:
        for item in recent_users:
            username = f"@{item['username']}" if item["username"] else "sans pseudo"
            lines.append(
                f"- {item['first_name']} ({username}) - "
                f"{item['message_count']} msg, {item['callback_count']} boutons"
            )

    return "\n".join(lines)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user.id if user else None):
        await update.effective_message.reply_text(_owner_required_text())
        return

    await update.effective_message.reply_text(_stats_text(), reply_markup=_owner_markup())


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user.id if user else None):
        await update.effective_message.reply_text(_owner_required_text())
        return

    text = (
        "Espace createur\n\n"
        "Actions disponibles:\n"
        "/stats - voir l'activite\n"
        "/broadcast <message> - envoyer un message aux utilisateurs connus"
    )
    await update.effective_message.reply_text(text, reply_markup=_owner_markup())


def _split_message(text: str, limit: int = 3900) -> list[str]:
    return [text[index : index + limit] for index in range(0, len(text), limit)] or [""]


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_owner(user.id if user else None):
        await update.effective_message.reply_text(_owner_required_text())
        return

    message = " ".join(context.args).strip()
    if not message:
        await update.effective_message.reply_text("Usage: /broadcast <message>")
        return

    chat_ids = list_user_chat_ids()
    count = 0
    for chat_id in chat_ids:
        try:
            for chunk in _split_message(f"Message de {BOT_NAME}\n\n{message}"):
                await context.bot.send_message(chat_id=chat_id, text=chunk)
            count += 1
        except Exception:
            continue

    await update.effective_message.reply_text(
        f"Broadcast termine: {count}/{len(chat_ids)} destinataires."
    )


from handlers.gemini_ai import ask_ai

async def conversation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message or not message.text:
        return
    await ask_ai(update, context)


async def _send_top(update: Update) -> None:
    message = update.effective_message
    if not message:
        return

    await message.reply_text("Je recupere le top anime...")
    top_items = await get_top_anime_api(limit=5)
    if not top_items:
        await message.reply_text("Erreur API pendant la recuperation du top.")
        return

    lines = ["Top 5 animes du moment:"]
    for index, anime in enumerate(top_items, start=1):
        title = anime.get("title", "Inconnu")
        score = anime.get("score", "N/A")
        lines.append(f"{index}. {title} - {score}")
    await message.reply_text("\n".join(lines))


async def _send_random(update: Update) -> None:
    message = update.effective_message
    if not message:
        return

    await message.reply_text("Je cherche un anime aleatoire...")
    anime = await get_random_anime_api()
    if not anime:
        await message.reply_text("Erreur API pendant la recherche aleatoire.")
        return

    await message.reply_text(format_anime_result(anime))


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    await query.answer()
    await remember_user(update, context, is_callback=True)
    data = query.data
    user = update.effective_user

    if data == "menu_main":
        await _edit_or_reply(update, f"Menu principal de {BOT_NAME}.", _main_menu_markup())
    elif data == "category_anime":
        await _edit_or_reply(
            update,
            "Anime\n\n/recherche <nom> pour chercher un anime.\n/random pour une decouverte.\n/top pour le classement.",
            _anime_markup(),
        )
    elif data == "category_downloads":
        await _edit_or_reply(
            update,
            "Telechargements\n\n/n <nom> - film/serie/episode\n/dl <lien> - TikTok/YouTube\n/op <anime> - opening\n/ed <anime> - ending\n/amv <anime> - AMV",
            _back_markup(),
        )
    elif data == "category_ai":
        await _edit_or_reply(
            update,
            "IA\n\n/ia <question> pour discuter avec Aizen.\n/clear pour effacer ton historique IA.",
            _back_markup(),
        )
    elif data == "category_fun":
        await _edit_or_reply(update, "Fun\n\nChoisis une reponse rapide.", _fun_markup())
    elif data == "category_tools":
        await _edit_or_reply(update, "Outils\n\nChoisis une action.", _tools_markup())
    elif data == "category_owner":
        if not is_owner(user.id if user else None):
            await update.effective_message.reply_text(_owner_required_text())
            return
        await _edit_or_reply(update, "Espace createur.", _owner_markup())
    elif data == "category_help":
        await help_command(update, context)
    elif data == "cmd_random":
        await _send_random(update)
    elif data == "cmd_top":
        await _send_top(update)
    elif data == "cmd_ping":
        await ping_command(update, context)
    elif data == "cmd_time":
        await time_command(update, context)
    elif data == "cmd_info":
        await info_command(update, context)
    elif data == "cmd_chatid":
        await chatid_command(update, context)
    elif data == "fun_love":
        await love_command(update, context)
    elif data == "fun_joke":
        await joke_command(update, context)
    elif data == "fun_quote":
        await quote_command(update, context)
    elif data == "fun_surprise":
        await surprise_command(update, context)
    elif data == "admin_stats":
        await stats_command(update, context)
    elif data == "admin_broadcast":
        await update.effective_message.reply_text("Usage: /broadcast <message>")


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.message.sticker:
        sticker_id = update.message.sticker.file_id
        await update.message.reply_text(
            f"ID de ce sticker :\n`{sticker_id}`\n\n"
            f"Copie-le et ajoute-le dans la ligne AIZEN_STICKERS= de ton fichier .env"
        )
