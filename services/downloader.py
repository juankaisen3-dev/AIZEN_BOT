import asyncio
import os
from pathlib import Path

import yt_dlp

from config import DOWNLOAD_PATH, MAX_FILE_SIZE

Path(DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)


async def search_youtube(query: str) -> str | None:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "force_generic_extractor": False,
    }

    def _search():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                search_query = query if query.startswith("http") else f"ytsearch1:{query}"
                info = ydl.extract_info(search_query, download=False)
                if not info:
                    return None

                if "entries" in info and info["entries"]:
                    entry = info["entries"][0]
                else:
                    entry = info

                return (
                    entry.get("webpage_url")
                    or entry.get("url")
                    or (
                        f"https://www.youtube.com/watch?v={entry['id']}"
                        if entry.get("id")
                        else None
                    )
                )
            except Exception:
                return None

    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _search)


async def download_youtube_video(url: str, category: str) -> str | None:
    if "tiktok.com" in url or "vm.tiktok" in url or "vt.tiktok" in url:
        import time
        import aiohttp
        import urllib.parse

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        encoded_url = urllib.parse.quote(url, safe="")

        # Liste d'APIs TikTok gratuites en cascade
        tiktok_apis = [
            {
                "url": f"https://api.tikmate.app/api/lookup?url={encoded_url}",
                "method": "GET",
                "extract": lambda d: d.get("token") and f"https://tikmate.app/download/{d['token']}/0.mp4",
            },
            {
                "url": "https://www.tikwm.com/api/",
                "method": "POST",
                "data": {"url": url, "hd": "1"},
                "extract": lambda d: d.get("code") == 0 and d["data"]["play"],
            },
            {
                "url": f"https://tiktok-downloader-download-tiktok-videos-without-watermark.p.rapidapi.com/index?url={encoded_url}",
                "method": "GET",
                "extract": lambda d: (d.get("video") or [None])[0],
            },
        ]

        async with aiohttp.ClientSession(headers=headers) as session:
            for api in tiktok_apis:
                try:
                    if api["method"] == "GET":
                        async with session.get(api["url"], timeout=15) as resp:
                            if resp.status == 200:
                                data = await resp.json(content_type=None)
                                video_url = api["extract"](data)
                            else:
                                continue
                    else:
                        async with session.post(api["url"], data=api.get("data"), timeout=15) as resp:
                            if resp.status == 200:
                                data = await resp.json(content_type=None)
                                video_url = api["extract"](data)
                            else:
                                continue

                    if video_url:
                        async with session.get(video_url) as video_resp:
                            if video_resp.status == 200:
                                filename = str(Path(DOWNLOAD_PATH) / f"{category}-tiktok-{int(time.time())}.mp4")
                                with open(filename, "wb") as f:
                                    f.write(await video_resp.read())
                                if os.path.getsize(filename) > MAX_FILE_SIZE * 1024 * 1024:
                                    os.remove(filename)
                                    return None
                                return filename
                except Exception as e:
                    print(f"API TikTok failed ({api['url'][:40]}): {e}")
                    continue

        print("Toutes les APIs TikTok ont echoue pour ce lien.")
        return None


    # System de fallback sur les resolutions pour rester sous les 50MB
    resolutions = [720, 480, 360, 240, 144]
    
    for res in resolutions:
        print(f"Tentative de telechargement en {res}p...")
        output_template = str(Path(DOWNLOAD_PATH) / f"{category}-%(id)s-{res}.%(ext)s")
        ydl_opts = {
            "format": f"best[ext=mp4][height<={res}]/bestvideo[ext=mp4][height<={res}]+bestaudio[ext=m4a]/best[ext=mp4]/bestvideo+bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "restrictfilenames": True,
        }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    return filename
                except Exception as exc:
                    print(f"Erreur download {res}p: {exc}")
                    return None

        loop = asyncio.get_running_loop()
        filename = await loop.run_in_executor(None, _download)

        if filename and os.path.exists(filename):
            size_mb = os.path.getsize(filename) / (1024 * 1024)
            if size_mb <= MAX_FILE_SIZE:
                print(f"Succes en {res}p ({size_mb:.1f}MB)")
                return filename
            else:
                print(f"Fichier {res}p trop gros ({size_mb:.1f}MB), suppression et tentative resolution inferieure.")
                os.remove(filename)
        else:
            continue

    return None


async def download_audio(url: str) -> str | None:
    """Telecharge uniquement l'audio d'une video YouTube (MP3 si FFmpeg dispo, sinon format natif)."""
    output_template = str(Path(DOWNLOAD_PATH) / "audio-%(id)s.%(ext)s")

    # Essai 1 : avec FFmpeg → MP3
    ydl_opts_mp3 = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "restrictfilenames": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }

    # Essai 2 : sans FFmpeg → format natif (m4a, webm, etc.)
    ydl_opts_native = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "restrictfilenames": True,
    }

    def _try_download(opts):
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                base = ydl.prepare_filename(info)
                # Cherche le fichier genere (mp3 ou natif)
                for ext in [".mp3", ".m4a", ".webm", ".opus", ".ogg"]:
                    candidate = str(Path(base).with_suffix(ext))
                    if os.path.exists(candidate):
                        return candidate
                # Fallback: cherche tout fichier audio genere pour cet ID
                for f in Path(DOWNLOAD_PATH).glob(f"audio-{info['id']}*"):
                    return str(f)
                return None
            except Exception as exc:
                print(f"Erreur download audio: {exc}")
                return None

    loop = asyncio.get_running_loop()

    # Tentative MP3 d'abord
    result = await loop.run_in_executor(None, _try_download, ydl_opts_mp3)
    if result and os.path.exists(result):
        if os.path.getsize(result) > MAX_FILE_SIZE * 1024 * 1024:
            os.remove(result)
            return None
        return result

    # Fallback format natif (sans FFmpeg)
    result = await loop.run_in_executor(None, _try_download, ydl_opts_native)
    if result and os.path.exists(result):
        if os.path.getsize(result) > MAX_FILE_SIZE * 1024 * 1024:
            os.remove(result)
            return None
        return result

    return None

