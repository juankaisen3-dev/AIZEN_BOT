import os

from telegram import Update
from telegram.ext import ContextTypes

from database.cache import save_download_record
from services.downloader import download_youtube_video, search_youtube


async def _download_and_send(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    command: str,
    suffix: str,
    category: str,
    search_message: str,
    caption_prefix: str,
):
    if not context.args:
        await update.message.reply_text(f"Usage: /{command} <nom_anime>")
        return

    base_query = " ".join(context.args)
    query = f"{base_query} {suffix}".strip()
    user_id = update.effective_user.id if update.effective_user else 0

    await update.message.reply_text(search_message.format(query=query))

    video_url = await search_youtube(query)
    if not video_url:
        save_download_record(user_id, query, category, "", "not_found")
        await update.message.reply_text("Aucune video trouvee.")
        return

    await update.message.reply_text("Telechargement en cours... cela peut prendre un moment.")
    file_path = await download_youtube_video(video_url, category)

    if not file_path or not os.path.exists(file_path):
        save_download_record(user_id, query, category, video_url, "failed")
        await update.message.reply_text(
            "Echec du telechargement. Si c'est un film ou episode entier, "
            "le fichier depasse probablement la limite de 50 Mo imposee par Telegram."
        )
        return

    try:
        with open(file_path, "rb") as stream:
            await update.message.reply_video(
                video=stream,
                caption=f"{caption_prefix} {query}\nTelechargement termine.",
                supports_streaming=True,
            )
        save_download_record(user_id, query, category, video_url, "success")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def download_op(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _download_and_send(
        update=update,
        context=context,
        command="op",
        suffix="opening",
        category="opening",
        search_message="Recherche de l'opening de {query}...",
        caption_prefix="Opening:",
    )


async def download_ed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _download_and_send(
        update=update,
        context=context,
        command="ed",
        suffix="ending",
        category="ending",
        search_message="Recherche de l'ending de {query}...",
        caption_prefix="Ending:",
    )


async def download_amv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _download_and_send(
        update=update,
        context=context,
        command="amv",
        suffix="amv",
        category="amv",
        search_message="Recherche d'AMV pour {query}...",
        caption_prefix="AMV:",
    )

async def download_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /dl <lien_tiktok_ou_youtube>")
        return

    query = context.args[0]
    if not query.startswith("http"):
        await update.message.reply_text("Il me faut un lien valide commencant par http (TikTok, YouTube, etc).")
        return

    # On recupere l'ID utilisateur
    user_id = update.effective_user.id if update.effective_user else 0

    await update.message.reply_text("Telechargement en cours... patiente un instant.")
    
    # Pour un lien direct, on le passe directement au telechargeur pour eviter une double requete
    # (TikTok bloque souvent si on fait trop de requetes d'un coup)
    file_path = await download_youtube_video(query, "video")

    if not file_path or not os.path.exists(file_path):
        save_download_record(user_id, query, "lien_direct", query, "failed")
        await update.message.reply_text(
            "Echec du telechargement. Si c'est un TikTok ou une video privee, "
            "le site peut bloquer l'acces au bot."
        )
        return

    try:
        with open(file_path, "rb") as stream:
            await update.message.reply_video(
                video=stream,
                caption="Voici ta video !",
                supports_streaming=True,
            )
        save_download_record(user_id, query, "lien_direct", query, "success")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def download_any(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _download_and_send(
        update=update,
        context=context,
        command="n",
        suffix="",
        category="general",
        search_message="Recherche de ton episode/film {query} (Note: limite a 50MB par Telegram)...",
        caption_prefix="Voici ta video :",
    )


async def download_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /song — telecharge une chanson depuis YouTube en MP3."""
    from services.downloader import download_audio

    if not context.args:
        await update.message.reply_text("Usage: /song <titre de la chanson>")
        return

    query = " ".join(context.args)
    user_id = update.effective_user.id if update.effective_user else 0

    await update.message.reply_text(f"Recherche de '{query}' sur YouTube... 🎵")

    video_url = await search_youtube(f"{query} audio")
    if not video_url:
        await update.message.reply_text("Aucun resultat trouve pour cette chanson.")
        return

    await update.message.reply_text("Telechargement audio en cours... ⏳")
    file_path = await download_audio(video_url)

    if not file_path or not os.path.exists(file_path):
        await update.message.reply_text(
            "Echec du telechargement. Essaie avec un autre titre.\n"
            "(Note: FFmpeg doit etre installe pour convertir en MP3)"
        )
        return

    try:
        with open(file_path, "rb") as stream:
            await update.message.reply_audio(
                audio=stream,
                caption=f"🎵 {query}",
                title=query,
            )
        save_download_record(user_id, query, "song", video_url, "success")
    except Exception as e:
        await update.message.reply_text(f"Erreur lors de l'envoi du fichier: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def generate_image_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Commande /img — genere une image via Pollinations.ai (gratuit, sans cle)."""
    import aiohttp
    import urllib.parse

    if not context.args:
        await update.message.reply_text("Usage: /img <description de l'image>")
        return

    prompt = " ".join(context.args)
    await update.message.reply_text(f"Generation de l'image en cours... 🎨\n'{prompt}'")

    encoded_prompt = urllib.parse.quote(prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url, timeout=60) as resp:
                if resp.status == 200:
                    image_data = await resp.read()
                    await update.message.reply_photo(
                        photo=image_data,
                        caption=f"🎨 {prompt}",
                    )
                else:
                    await update.message.reply_text("Echec de la generation, reessaie dans quelques secondes.")
    except Exception as e:
        await update.message.reply_text(f"Erreur de generation: {e}")
