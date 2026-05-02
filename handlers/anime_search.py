from telegram import Update
from telegram.ext import ContextTypes

from services.jikan_client import (
    get_random_anime_api,
    get_top_anime_api,
    search_anime_api,
)


async def search_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /recherche <nom_anime>")
        return

    query = " ".join(context.args)
    await update.message.reply_text(f"Recherche de {query}...")

    anime = await search_anime_api(query)
    if not anime:
        await update.message.reply_text(f"Aucun anime trouve pour {query}.")
        return

    await send_anime_result(update, anime)


def format_anime_result(anime: dict) -> str:
    title = anime.get("title", "Inconnu")
    title_jp = anime.get("title_japanese") or "N/A"
    score = anime.get("score", "N/A")
    episodes = anime.get("episodes", "?")
    status = anime.get("status", "Inconnu")
    synopsis = anime.get("synopsis") or "Pas de synopsis."
    if len(synopsis) > 500:
        synopsis = synopsis[:500] + "..."

    genres = ", ".join(item["name"] for item in anime.get("genres", [])) or "N/A"
    studios = ", ".join(item["name"] for item in anime.get("studios", [])) or "N/A"

    return (
        f"Anime: {title}\n"
        f"Titre JP: {title_jp}\n"
        f"Note: {score}/10\n"
        f"Episodes: {episodes}\n"
        f"Statut: {status}\n"
        f"Genres: {genres}\n"
        f"Studios: {studios}\n\n"
        f"Synopsis:\n{synopsis}\n\n"
        f"Commandes utiles:\n"
        f"/op {title}\n"
        f"/ia Parle moi de {title}"
    )


async def send_anime_result(update: Update, anime: dict):
    await update.effective_message.reply_text(format_anime_result(anime))


async def random_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    anime = await get_random_anime_api()
    if not anime:
        await update.message.reply_text("Erreur API.")
        return

    await send_anime_result(update, anime)


async def top_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_items = await get_top_anime_api(limit=5)
    if not top_items:
        await update.message.reply_text("Erreur API.")
        return

    lines = ["Top 5 animes du moment:"]
    for index, anime in enumerate(top_items, start=1):
        lines.append(f"{index}. {anime['title']} - {anime['score']}")

    await update.message.reply_text("\n".join(lines))
