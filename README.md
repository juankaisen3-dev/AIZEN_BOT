# Aizen Bot

Un bot Telegram pour la recherche d'anime, le telechargement YouTube et l'IA Gemini.

## Installation

1. Installe les dependances :
   ```
   pip install -r requirements.txt
   ```

2. Configure les variables d'environnement dans `.env` :
   - `BOT_TOKEN` : ton token Telegram
   - `GEMINI_API_KEY` : ta cle API Gemini
   - `DOWNLOAD_PATH` : dossier de sortie des videos
   - `MAX_FILE_SIZE` : taille maximale en Mo pour Telegram
   - `BOT_NAME` : nom affiche du bot, defaut `Aizen`
   - `BOT_CREATOR` : nom du createur, defaut `Oyougou Daniel`
   - `BOT_CREATOR_PSEUDO` : pseudo du createur, defaut `Le Shinigami`
   - `BOT_PERSONALITY` : style/personnalite du bot
   - `BOT_OWNER_IDS` : IDs Telegram admin separes par des virgules, utile pour `/admin`, `/stats` et `/broadcast`
   - `TELEGRAM_PROXY_URL` : proxy optionnel si Telegram est bloque sur ton reseau
   - `TELEGRAM_CONNECT_TIMEOUT` : timeout de connexion Telegram en secondes, defaut `30`
   - `TELEGRAM_BOOTSTRAP_RETRIES` : tentatives au demarrage, defaut `5`
   - `TELEGRAM_RETRY_DELAY` : delai entre deux tentatives si Telegram est inaccessible, defaut `30`
   - `TELEGRAM_REQUIRE_NETWORK_CHECK` : mets `1` pour quitter immediatement si Telegram est inaccessible, defaut `0`
   - `TELEGRAM_RETRY_WITHOUT_PROXY` : mets `1` pour continuer a reessayer meme sans proxy, defaut `0`

`TELEGRAM_BOT_TOKEN` reste accepte comme variable legacy si ton `.env` existe deja, mais `BOT_TOKEN` est le nom recommande.

## Utilisation

Lance le bot :

```
python bot.py
```

Commandes principales :

```
/start
/menu
/aide
/recherche Naruto
/random
/top
/op Naruto
/ed Naruto
/amv Naruto
/ia Recommande-moi un anime
/info
/creator
/ping
/time
/chatid
/love
/joke
/quote
/surprise
```

Commandes createur :

```
/admin
/stats
/broadcast Ton message
```

Utilise `/chatid` pour recuperer ton ID Telegram, puis ajoute-le dans `BOT_OWNER_IDS`.

Pour verifier uniquement les fichiers du projet, utilise :

```
python -m compileall -q bot.py config.py handlers services database
```

Ne lance pas `python -m compileall` sans chemin : Python va aussi parcourir sa propre installation (`C:\Python314\Lib`, `site-packages`, etc.).

## Depannage

- Verifie que `BOT_TOKEN` et `GEMINI_API_KEY` sont bien definis.
- Si le demarrage affiche `Timed out`, teste l'acces a Telegram avec `curl.exe -I https://api.telegram.org --connect-timeout 15`. Si cette commande expire aussi, le probleme vient du reseau, du pare-feu, du VPN ou du fournisseur d'acces. Configure alors `TELEGRAM_PROXY_URL` dans `.env`, par exemple `http://127.0.0.1:7890`.
- Si tu vois `WinError 10060`, ta machine ne joint pas Telegram en direct. Lance un VPN/proxy qui autorise Telegram, puis mets son adresse HTTP/SOCKS dans `TELEGRAM_PROXY_URL`. Sans proxy configure, le bot s'arrete avec un message clair au lieu de boucler.
- Pour trouver un proxy local deja lance sous Windows :
  ```
  Get-NetTCPConnection -State Listen | Where-Object { $_.LocalAddress -in @('127.0.0.1','0.0.0.0') -and $_.LocalPort -in @(7890,10808,9050) }
  ```
- Garde une seule ligne `TELEGRAM_PROXY_URL` dans `.env`. Avant de lancer le bot, verifie que ton proxy local est demarre et que son port repond, par exemple `Test-NetConnection 127.0.0.1 -Port 10808`.
- Le bot accepte aussi les variables de proxy standard `HTTPS_PROXY`, `HTTP_PROXY` et `ALL_PROXY`.
- Si Gemini ne repond pas, verifie l'acces API et la cle configuree dans `.env`.
- Pour les telechargements YouTube, `yt-dlp` peut necessiter des dependances supplementaires selon le systeme.
