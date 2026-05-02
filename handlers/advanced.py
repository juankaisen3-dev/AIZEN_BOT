"""
Handlers pour les features avancees :
- /fav      : Ajouter un anime en favori
- /unfav    : Retirer un favori
- /mesfavs  : Voir sa liste de favoris avec scores
- /note     : Noter un anime dans ses favoris (1-10)
- /montop   : Voir son top perso classe par note
- /rappel   : Creer un rappel
- /mesrappels : Voir ses rappels actifs
"""

import re
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes

from database.cache import (
    add_favorite,
    add_reminder,
    get_favorites,
    get_pending_reminders,
    mark_reminder_sent,
    remove_favorite,
    update_favorite_score,
)


# ─── FAVORIS ─────────────────────────────────────────────────────────────────

async def fav_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ajoute un anime en favori. Usage: /fav <nom anime> [note 1-10]"""
    if not context.args:
        await update.message.reply_text("Usage: /fav <nom anime> [note 1-10]\nEx: /fav Bleach 10")
        return

    user_id = update.effective_user.id

    # Detecte si le dernier arg est une note
    score = 0
    args = list(context.args)
    if args[-1].isdigit() and 1 <= int(args[-1]) <= 10:
        score = int(args.pop())

    anime_name = " ".join(args)
    added = add_favorite(user_id, anime_name, score)

    if added:
        msg = f"✅ *{anime_name}* ajouté à tes favoris !"
        if score:
            msg += f" ⭐ Note: {score}/10"
    else:
        msg = f"⚠️ *{anime_name}* est déjà dans tes favoris !"

    await update.message.reply_text(msg, parse_mode="Markdown")


async def unfav_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Retire un anime des favoris. Usage: /unfav <nom anime>"""
    if not context.args:
        await update.message.reply_text("Usage: /unfav <nom anime>")
        return

    user_id = update.effective_user.id
    anime_name = " ".join(context.args)
    removed = remove_favorite(user_id, anime_name)

    if removed:
        await update.message.reply_text(f"🗑️ *{anime_name}* retiré de tes favoris.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ *{anime_name}* n'est pas dans tes favoris.", parse_mode="Markdown")


async def mesfavs_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche la liste des favoris."""
    user_id = update.effective_user.id
    favs = get_favorites(user_id)

    if not favs:
        await update.message.reply_text(
            "Ta liste de favoris est vide 😅\nUtilise /fav <anime> pour en ajouter !"
        )
        return

    lines = ["🎌 *Tes animes favoris :*\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, score) in enumerate(favs):
        medal = medals[i] if i < 3 else f"{i+1}."
        stars = f" ⭐ {score}/10" if score else ""
        lines.append(f"{medal} {name}{stars}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Note un anime dans les favoris. Usage: /note <nom anime> <1-10>"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: /note <nom anime> <1-10>\nEx: /note Bleach 10")
        return

    user_id = update.effective_user.id
    args = list(context.args)
    score_str = args[-1]

    if not score_str.isdigit() or not (1 <= int(score_str) <= 10):
        await update.message.reply_text("La note doit etre un chiffre entre 1 et 10.")
        return

    score = int(args.pop())
    anime_name = " ".join(args)
    updated = update_favorite_score(user_id, anime_name, score)

    if updated:
        await update.message.reply_text(
            f"⭐ *{anime_name}* noté *{score}/10* dans tes favoris !",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"❌ *{anime_name}* n'est pas dans tes favoris.\nAjoute-le d'abord avec /fav {anime_name}",
            parse_mode="Markdown",
        )


async def montop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Affiche le top perso de l'utilisateur (animes notes)."""
    user_id = update.effective_user.id
    favs = get_favorites(user_id)
    top = [(n, s) for n, s in favs if s > 0]

    if not top:
        await update.message.reply_text(
            "Ton top est vide 😅\nNote tes animes avec /note <anime> <1-10> pour construire ton classement !"
        )
        return

    lines = [f"🏆 *Ton Top Anime Personnel :*\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, score) in enumerate(top):
        medal = medals[i] if i < 3 else f"#{i+1}"
        bar = "⭐" * (score // 2)
        lines.append(f"{medal} *{name}* — {score}/10 {bar}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── RAPPELS ─────────────────────────────────────────────────────────────────

def _parse_duration(text: str) -> timedelta | None:
    """Convertit '20min', '2h', '1j' en timedelta."""
    pattern = re.match(r"^(\d+)(s|sec|min|h|hr|j|jour|jours|d)$", text.lower())
    if not pattern:
        return None
    val = int(pattern.group(1))
    unit = pattern.group(2)
    if unit in ("s", "sec"):
        return timedelta(seconds=val)
    if unit == "min":
        return timedelta(minutes=val)
    if unit in ("h", "hr"):
        return timedelta(hours=val)
    if unit in ("j", "jour", "jours", "d"):
        return timedelta(days=val)
    return None


async def rappel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cree un rappel. Usage: /rappel <duree> <message>
    Exemples: /rappel 20min regarder Bleach
              /rappel 2h checker les nouveaux episodes
    """
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /rappel <duree> <message>\n"
            "Exemples:\n"
            "• /rappel 20min regarder Bleach\n"
            "• /rappel 2h checker les episodes\n"
            "• /rappel 1j finir One Piece\n\n"
            "Unites: s, min, h, j"
        )
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    duration_str = context.args[0]
    message = " ".join(context.args[1:])

    delta = _parse_duration(duration_str)
    if not delta:
        await update.message.reply_text(
            f"❌ Duree invalide : `{duration_str}`\nUtilise : 20min, 2h, 1j",
            parse_mode="Markdown",
        )
        return

    remind_at = datetime.now() + delta
    add_reminder(user_id, chat_id, message, remind_at)

    # Formater le temps
    if delta.total_seconds() < 3600:
        duree_lisible = f"{int(delta.total_seconds() // 60)} minutes"
    elif delta.total_seconds() < 86400:
        duree_lisible = f"{int(delta.total_seconds() // 3600)} heure(s)"
    else:
        duree_lisible = f"{delta.days} jour(s)"

    await update.message.reply_text(
        f"⏰ Rappel enregistre !\n\n"
        f"📝 *{message}*\n"
        f"🕐 Dans {duree_lisible} ({remind_at.strftime('%H:%M:%S')})",
        parse_mode="Markdown",
    )


async def check_reminders(context) -> None:
    """Tache planifiee — verifie et envoie les rappels en attente."""
    pending = get_pending_reminders()
    for reminder_id, user_id, chat_id, message in pending:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ *Rappel !*\n\n📝 {message}",
                parse_mode="Markdown",
            )
            mark_reminder_sent(reminder_id)
        except Exception as e:
            print(f"Erreur envoi rappel {reminder_id}: {e}")
