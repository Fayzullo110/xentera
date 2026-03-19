import logging
import os
import re
import subprocess
import json
import requests
import asyncio
from urllib.parse import urlparse, parse_qs
import time
import base64
import hashlib
import hmac
import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import Config

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Helper functions for URL detection and parsing
import re
from urllib.parse import urlparse, parse_qs

def extract_urls(text):
    """Extract URLs from text"""
    url_pattern = re.compile(r'(https?://[^\s]+)')
    return url_pattern.findall(text)

def is_youtube_url(url):
    """Check if URL is a YouTube URL"""
    parsed = urlparse(url)
    return parsed.netloc in ('www.youtube.com', 'youtube.com', 'youtu.be', 'm.youtube.com')

def is_instagram_url(url):
    """Check if URL is an Instagram URL"""
    parsed = urlparse(url)
    return parsed.netloc in ('www.instagram.com', 'instagram.com', 'www.instagr.am', 'instagr.am')

def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    parsed = urlparse(url)
    if parsed.netloc in ('youtu.be', 'www.youtu.be'):
        return parsed.path.lstrip('/')
    if parsed.netloc in ('www.youtube.com', 'youtube.com', 'm.youtube.com'):
        if parsed.path == '/watch':
            qs = parse_qs(parsed.query)
            return qs.get('v', [None])[0]
        if parsed.path.startswith('/embed/'):
            return parsed.path.split('/')[2]
        if parsed.path.startswith('/v/'):
            return parsed.path.split('/')[2]
    return None

USER_LANG_FILE = "user_langs.json"

TRANSLATIONS = {
    "en": {
        "choose_lang": "🌐 Choose language / Tilni tanlang / Выберите язык:",
        "lang_set": "✅ Language set.",
        "start_greeting": "Hi {name}! 👋\n\nWelcome to {bot}!",
        "help": "🎵 **{bot} - Smart Music Bot**\n\n🎵 **How it works**:\n1. Just type an artist name (e.g., 'The Weeknd')\n2. Choose a song from the buttons below\n3. The bot downloads and sends the audio\n\n📄 Use Next/Previous to navigate pages\n\nOther features:\n/check @username - Cross-platform account verification\n/photo - Photo analysis\n\n💡 Just type any artist name to get started!",
        "about": "🤖 {bot}\n\nA Telegram bot created with python-telegram-bot library.",
        "need_query": "🎵 Please provide an artist or song name! Example: The Weeknd",
        "searching": "🔍 Searching for: {query}...\nThis may take a few seconds.",
        "found": "🎵 **Found {count} songs for:** {query}\n\n📄 **Page {page}** (Songs {start}-{end}):\n\n",
    },
    "uz": {
        "choose_lang": "🌐 Tilni tanlang / Choose language / Выберите язык:",
        "lang_set": "✅ Til saqlandi.",
        "start_greeting": "Salom {name}! 👋\n\n{bot} botiga xush kelibsiz!",
        "help": "🎵 **{bot} - Musiqa bot**\n\n🎵 **Qanday ishlaydi**:\n1. Ijrochi yoki qo‘shiq nomini yozing (masalan, 'The Weeknd')\n2. Pastdagi tugmalardan qo‘shiqni tanlang\n3. Bot yuklab olib audio yuboradi\n\n📄 Keyingi/Oldingi tugmalari bilan sahifalarni almashtiring\n\nBoshqa imkoniyatlar:\n/check @username - Profil tekshirish\n/photo - Foto tahlil\n\n💡 Boshlash uchun ijrochi nomini yozing!",
        "about": "🤖 {bot}\n\npython-telegram-bot kutubxonasi bilan yaratilgan bot.",
        "need_query": "🎵 Ijrochi yoki qo‘shiq nomini kiriting! Masalan: The Weeknd",
        "searching": "🔍 Qidirilmoqda: {query}...\nBu bir necha soniya olishi mumkin.",
        "found": "🎵 **{query} uchun {count} ta qo‘shiq topildi**\n\n📄 **Sahifa {page}** (Qo‘shiqlar {start}-{end}):\n\n",
    },
    "ru": {
        "choose_lang": "🌐 Выберите язык / Choose language / Tilni tanlang:",
        "lang_set": "✅ Язык установлен.",
        "start_greeting": "Привет, {name}! 👋\n\nДобро пожаловать в {bot}!",
        "help": "🎵 **{bot} - Музыкальный бот**\n\n🎵 **Как это работает**:\n1. Просто напишите исполнителя (например, 'The Weeknd')\n2. Выберите песню кнопкой ниже\n3. Бот скачает и отправит аудио\n\n📄 Кнопки Далее/Назад переключают страницы\n\nДругие функции:\n/check @username - Проверка профиля\n/photo - Анализ фото\n\n💡 Просто напишите имя исполнителя, чтобы начать!",
        "about": "🤖 {bot}\n\nБот на python-telegram-bot.",
        "need_query": "🎵 Напишите исполнителя или название песни! Например: The Weeknd",
        "searching": "🔍 Ищу: {query}...\nЭто может занять несколько секунд.",
        "found": "🎵 **Найдено {count} песен по запросу:** {query}\n\n📄 **Страница {page}** (Песни {start}-{end}):\n\n",
    },
}


def _load_user_langs() -> dict:
    if not os.path.exists(USER_LANG_FILE):
        return {}
    try:
        with open(USER_LANG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_user_langs(data: dict) -> None:
    try:
        with open(USER_LANG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_user_lang(user_id: int) -> str:
    data = _load_user_langs()
    lang = data.get(str(user_id))
    return lang if lang in TRANSLATIONS else "en"


def set_user_lang(user_id: int, lang: str) -> None:
    if lang not in TRANSLATIONS:
        return
    data = _load_user_langs()
    data[str(user_id)] = lang
    _save_user_langs(data)


def t(user_id: int, key: str, **kwargs) -> str:
    lang = get_user_lang(user_id)
    template = TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))
    try:
        return template.format(**kwargs)
    except Exception:
        return template


async def delete_later(msg, delay: int) -> None:
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except Exception:
        pass


def acrcloud_is_configured() -> bool:
    return bool(Config.ACRCLOUD_HOST and Config.ACRCLOUD_ACCESS_KEY and Config.ACRCLOUD_ACCESS_SECRET)


def acrcloud_identify(file_path: str) -> dict | None:
    """Identify music using ACRCloud API.

    Returns a dict with keys: title, artist, album (best-effort) or None.
    """
    if not acrcloud_is_configured():
        return None

    host = (Config.ACRCLOUD_HOST or "").strip()
    if not host:
        return None
    if not host.startswith("http"):
        host = "https://" + host

    http_method = "POST"
    http_uri = "/v1/identify"
    data_type = "audio"
    signature_version = "1"
    timestamp = str(int(time.time()))

    string_to_sign = "\n".join([
        http_method,
        http_uri,
        Config.ACRCLOUD_ACCESS_KEY or "",
        data_type,
        signature_version,
        timestamp,
    ])
    sign = base64.b64encode(
        hmac.new(
            (Config.ACRCLOUD_ACCESS_SECRET or "").encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha1,
        ).digest()
    ).decode("utf-8")

    url = host.rstrip("/") + http_uri

    try:
        with open(file_path, "rb") as f:
            sample = f.read()
    except Exception:
        return None

    files = {
        "sample": (os.path.basename(file_path), sample),
    }
    data = {
        "access_key": Config.ACRCLOUD_ACCESS_KEY or "",
        "data_type": data_type,
        "signature_version": signature_version,
        "signature": sign,
        "timestamp": timestamp,
        "sample_bytes": str(len(sample)),
    }

    try:
        resp = requests.post(url, data=data, files=files, timeout=30)
        payload = resp.json()
    except Exception:
        return None

    if payload.get("status", {}).get("code") != 0:
        return None

    musics = (((payload.get("metadata") or {}).get("music")) or [])
    if not musics:
        return None
    best = musics[0] or {}

    title = (best.get("title") or "").strip()
    artists = best.get("artists") or []
    artist = ""
    if artists and isinstance(artists, list) and isinstance(artists[0], dict):
        artist = (artists[0].get("name") or "").strip()
    album = ((best.get("album") or {}).get("name") or "").strip() if isinstance(best.get("album"), dict) else ""

    if not title:
        return None
    return {"title": title, "artist": artist, "album": album}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user

    langs = _load_user_langs()
    if str(user.id) not in langs:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        buttons = [
            [InlineKeyboardButton("English", callback_data="lang_en")],
            [InlineKeyboardButton("O'zbek", callback_data="lang_uz")],
            [InlineKeyboardButton("Русский", callback_data="lang_ru")],
        ]
        await update.message.reply_text(
            TRANSLATIONS["en"]["choose_lang"],
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    await update.message.reply_text(
        t(user.id, "start_greeting", name=user.first_name, bot=Config.BOT_NAME)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        t(update.effective_user.id, "help", bot=Config.BOT_NAME)
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /about is issued."""
    await update.message.reply_text(
        t(update.effective_user.id, "about", bot=Config.BOT_NAME)
    )

async def verify_telegram(username: str) -> bool:
    """Check if Telegram account exists by checking profile page"""
    try:
        url = f"https://t.me/{username}"
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        # Telegram returns 200 for existing accounts, 404 for non-existing
        return response.status_code == 200 and 'tgme_page_title' in response.text
    except:
        return False

async def verify_facebook(username: str) -> bool:
    """Check if Facebook account exists by checking profile page"""
    try:
        url = f"https://www.facebook.com/{username}"
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        # Facebook redirects or shows error for non-existing accounts
        return response.status_code == 200 and 'content="0; url' not in response.text
    except:
        return False

async def handle_music_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle music search and song selection"""
    if not context.args:
        await update.message.reply_text(t(update.message.from_user.id, "need_query"))
        return
    
    query = " ".join(context.args)
    user_id = update.message.from_user.id
    
    # Check if user is selecting a song (number) or searching (text)
    if len(context.args) == 1 and context.args[0].isdigit():
        # User is selecting a song to download
        await handle_song_selection(update.message, int(context.args[0]), update.message.from_user.id)
    else:
        # User is searching for songs
        await search_songs(update.message, query, update.message.from_user.id)

async def search_songs(message, query: str, user_id: int):
    """Search for songs on YouTube and show results"""
    status_msg = await message.reply_text(f"🔍 Searching for: {query}...")
    
    try:
        import subprocess
        import json
        
        cmd = [
            'yt-dlp', 
            '--flat-playlist',
            '--match-filter', 'duration < 600',
            '--reject-title', '(?i)(live|interview|reaction|podcast|mix|remix|cover|sped up|slowed|full album|concert)',
            '--dump-json', 
            '--no-download',
            f'ytsearch20:{query} audio'  # Get more results for pagination
        ]
        
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        
        if result.returncode == 0:
            # Parse the JSON output (it might be multiple JSON objects or a single line)
            try:
                # Try to parse as a single JSON object first
                data = json.loads(result.stdout.strip())
                if isinstance(data, list):
                    videos = data
                elif isinstance(data, dict) and 'entries' in data:
                    videos = data['entries']
                else:
                    videos = []
            except:
                # Fallback: try parsing line by line
                videos = []
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        try:
                            video_data = json.loads(line)
                            if isinstance(video_data, dict) and 'url' in video_data:
                                videos.append(video_data)
                        except:
                            continue
            
            if videos:
                # Store search results for pagination and download
                import pickle
                search_data = {
                    'query': query,
                    'videos': videos,
                    'page': 0,
                    'per_page': 5
                }
                with open(f"search_results_{user_id}.pkl", 'wb') as f:
                    pickle.dump(search_data, f)
                
                await show_songs_page(message, user_id, 0)
                asyncio.create_task(delete_later(searching_msg, 6))
            else:
                await message.reply_text(f"❌ No songs found for: {query}")
        else:
            await message.reply_text(f"❌ Error searching for: {query}")
            
    except subprocess.TimeoutExpired:
        await message.reply_text("⏰ Search timed out. Please try again.")
    except Exception as e:
        logger.error(f"Error in music search: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")


async def handle_video_link(message, url: str, user_id: int):
    status_msg = await message.reply_text("🔗 Detected a video link. Processing...")
    try:
        # YouTube: download directly
        if is_youtube_url(url):
            vid = extract_youtube_id(url)
            await process_download(message, url, "YouTube", user_id, vid)
            asyncio.create_task(delete_later(status_msg, 4))
            return

        # Instagram: best-effort extract title/description then search YouTube audio
        if is_instagram_url(url):
            # Option A (exact): try to download the Reel audio directly from Instagram first
            # This is the most accurate way to get the *same* sound as the Reel.
            try:
                meta_cmd = [
                    'yt-dlp',
                    '--dump-single-json',
                    '--no-download',
                    '--no-playlist',
                    url,
                ]
                meta_res = await asyncio.to_thread(
                    subprocess.run,
                    meta_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                meta = json.loads(meta_res.stdout) if meta_res.returncode == 0 and meta_res.stdout.strip() else {}
                ig_title = (meta.get('title') or "Instagram").strip() or "Instagram"
                ig_id = (meta.get('id') or "ig").strip() or "ig"
                ig_duration = meta.get('duration')
                try:
                    ig_duration = float(ig_duration) if ig_duration is not None else None
                except Exception:
                    ig_duration = None

                # If the Reel is short, prefer full song identification via ACRCloud (if configured).
                # If ACRCloud isn't configured, fall back to metadata-based matching below.
                if ig_duration is not None and ig_duration < 90:
                    safe_id = ig_id
                    tmp_dir = os.getenv("TMPDIR") or "/tmp"
                    base_name = f"{user_id}_{safe_id}_ig"
                    output_template = f"{tmp_dir}/{base_name}.%(ext)s"
                    os.makedirs(tmp_dir, exist_ok=True)

                    cmd = [
                        'yt-dlp',
                        '--no-playlist',
                        '--retries', '3',
                        '--fragment-retries', '3',
                        '--socket-timeout', '15',
                        '-f', 'bestaudio',
                        '-o', output_template,
                        url,
                    ]
                    result = await asyncio.to_thread(
                        subprocess.run,
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=600,
                    )

                    matches = glob.glob(f"{tmp_dir}/{base_name}.*") if result.returncode == 0 else []
                    clip_file = matches[0] if matches else None

                    if clip_file and os.path.exists(clip_file) and acrcloud_is_configured():
                        identified = acrcloud_identify(clip_file)
                        if identified:
                            q_artist = identified.get("artist") or ""
                            q_title = identified.get("title") or ""
                            query = f"{q_artist} - {q_title}".strip(" -")

                            await message.reply_text(f"🎧 Identified: {query}")

                            # Use YouTube Music search for the full track
                            ytm = await asyncio.to_thread(
                                subprocess.run,
                                [
                                    'yt-dlp',
                                    '--flat-playlist',
                                    '--dump-json',
                                    '--no-playlist',
                                    f'ytsearch1:{query} audio'
                                ],
                                capture_output=True,
                                text=True,
                                timeout=60,
                            )
                            if ytm.returncode == 0 and ytm.stdout.strip():
                                v = json.loads(ytm.stdout.strip().split('\n')[0])
                                v_url = v.get('url')
                                v_title = v.get('title', query)
                                v_id = v.get('id')
                                if v_url:
                                    await process_download(message, v_url, v_title, user_id, v_id)
                                    asyncio.create_task(delete_later(status_msg, 4))
                                    try:
                                        os.remove(clip_file)
                                    except Exception:
                                        pass
                                    return

                    if clip_file:
                        try:
                            os.remove(clip_file)
                        except Exception:
                            pass

                    # Fall back to matching below
                    raise RuntimeError("reel_short_fallback")

                # Download exact audio from the IG URL
                safe_id = ig_id
                tmp_dir = os.getenv("TMPDIR") or "/tmp"
                base_name = f"{user_id}_{safe_id}_igfull"
                output_template = f"{tmp_dir}/{base_name}.%(ext)s"
                os.makedirs(tmp_dir, exist_ok=True)

                start_msg = await message.reply_text(f"📥 Starting download: {ig_title}\nThis may take a while...")
                cmd = [
                    'yt-dlp',
                    '--no-playlist',
                    '--retries', '3',
                    '--fragment-retries', '3',
                    '--socket-timeout', '15',
                    '-f', 'bestaudio',
                    '-o', output_template,
                    url,
                ]
                result = await asyncio.to_thread(
                    subprocess.run,
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )

                matches = glob.glob(f"{tmp_dir}/{base_name}.*") if result.returncode == 0 else []
                downloaded_file = matches[0] if matches else None
                if downloaded_file and os.path.exists(downloaded_file):
                    with open(downloaded_file, 'rb') as f:
                        await message.reply_audio(audio=f, title=ig_title)
                    done_msg = await message.reply_text(f"✅ Download complete: {ig_title}\n📁 File: {downloaded_file}")
                    asyncio.create_task(delete_later(start_msg, 8))
                    asyncio.create_task(delete_later(done_msg, 8))
                    asyncio.create_task(delete_later(status_msg, 4))
                    try:
                        os.remove(downloaded_file)
                    except Exception:
                        pass
                    return

                # If Instagram download failed, fall back to matching below
            except Exception:
                pass

            meta_cmd = [
                'yt-dlp',
                '--dump-single-json',
                '--no-download',
                '--no-playlist',
                url,
            ]
            meta_res = await asyncio.to_thread(
                subprocess.run,
                meta_cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if meta_res.returncode != 0:
                await message.reply_text("❌ Could not read Instagram link (may require login/cookies). Try sending a YouTube link instead.")
                asyncio.create_task(delete_later(status_msg, 4))
                return

            try:
                meta = json.loads(meta_res.stdout)
            except Exception:
                meta = {}

            title = (meta.get('title') or "").strip()
            desc = (meta.get('description') or "").strip()
            track = (meta.get('track') or "").strip()
            artist = (meta.get('artist') or "").strip()
            uploader = (meta.get('uploader') or "").strip()
            ig_duration = meta.get('duration')
            try:
                ig_duration = float(ig_duration) if ig_duration is not None else None
            except Exception:
                ig_duration = None

            candidates: list[str] = []
            if artist and track:
                candidates.append(f"{artist} - {track}")
            if title:
                candidates.append(title)
            if track:
                candidates.append(track)
            if desc:
                candidates.append(desc)
            if uploader and title:
                candidates.append(f"{uploader} {title}")

            # Normalize and dedupe
            normalized: list[str] = []
            seen = set()
            for c in candidates:
                q = re.sub(r"\s+", " ", c).strip()
                if not q:
                    continue
                key = q.lower()
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(q)

            if not normalized:
                await message.reply_text("❌ Couldn't extract a search query from this Instagram link.")
                asyncio.create_task(delete_later(status_msg, 4))
                return

            min_full_duration = 90 if (ig_duration is not None and ig_duration < 90) else None

            def _search_and_pick(prefix: str, cmd_query: str, limit: int, strict: bool) -> dict | None:
                base = [
                    'yt-dlp',
                    '--flat-playlist',
                    '--dump-json',
                    '--no-download',
                ]
                if strict:
                    dur_filter = 'duration < 600'
                    if min_full_duration is not None:
                        dur_filter = f'duration < 600 & duration > {int(min_full_duration)}'
                    base += [
                        '--match-filter', dur_filter,
                        '--reject-title', '(?i)(live|interview|reaction|podcast|mix|remix|cover|sped up|slowed|full album|concert)',
                    ]
                else:
                    dur_filter = 'duration < 1200'
                    if min_full_duration is not None:
                        dur_filter = f'duration < 1200 & duration > {int(min_full_duration)}'
                    base += [
                        '--match-filter', dur_filter,
                    ]

                base.append(f'{prefix}{limit}:{cmd_query}')

                res = subprocess.run(base, capture_output=True, text=True, timeout=30)
                if res.returncode != 0 or not res.stdout.strip():
                    return None

                best: dict | None = None
                best_score: float | None = None
                for line in res.stdout.strip().split('\n'):
                    if not line.strip():
                        continue
                    try:
                        v = json.loads(line)
                    except Exception:
                        continue

                    # Prefer closer duration if Instagram duration is known
                    dur = v.get('duration')
                    try:
                        dur_f = float(dur) if dur is not None else None
                    except Exception:
                        dur_f = None

                    if ig_duration is not None and dur_f is not None:
                        score = abs(dur_f - ig_duration)
                    else:
                        score = 0.0

                    if min_full_duration is not None and dur_f is not None and dur_f < min_full_duration:
                        continue

                    if best is None or best_score is None or score < best_score:
                        best = v
                        best_score = score

                return best

            video: dict | None = None
            # 1) Prefer YouTube Music if we have track/artist
            if artist and track:
                video = _search_and_pick('ytmsearch', f"{artist} - {track}", 5, strict=True)

            # 2) Strict mode, try candidates on YouTube Music first
            if not video:
                for q in normalized:
                    video = _search_and_pick('ytmsearch', f"{q} audio", 5, strict=True)
                    if video:
                        break

            # 3) Strict mode, YouTube regular search
            if not video:
                for q in normalized:
                    video = _search_and_pick('ytsearch', f"{q} audio", 5, strict=True)
                    if video:
                        break

            # 4) Relaxed mode fallback, YouTube regular search
            if not video:
                for q in normalized:
                    video = _search_and_pick('ytsearch', q, 5, strict=False)
                    if video:
                        break

            if not video:
                await message.reply_text("❌ Could not find matching music for this Instagram link.")
                asyncio.create_task(delete_later(status_msg, 4))
                return

            video_url = video.get('url')
            video_title = video.get('title', 'Unknown')
            video_id = video.get('id')
            if not video_url:
                await message.reply_text("❌ Could not find a downloadable result.")
                asyncio.create_task(delete_later(status_msg, 4))
                return

            await process_download(message, video_url, video_title, user_id, video_id)
            asyncio.create_task(delete_later(status_msg, 4))
            return

        await message.reply_text("❌ Unsupported link. Send a YouTube or Instagram video link.")
        asyncio.create_task(delete_later(status_msg, 4))
    except subprocess.TimeoutExpired:
        await message.reply_text("⏰ Link processing timed out. Please try again.")
        asyncio.create_task(delete_later(status_msg, 4))
    except Exception as e:
        logger.error(f"Error processing link: {e}")
        await message.reply_text("❌ Failed to process this link.")
        asyncio.create_task(delete_later(status_msg, 4))

async def show_songs_page(message, user_id: int, page: int):
    """Show songs for a specific page with inline buttons"""
    import pickle
    import os
    
    results_file = f"search_results_{user_id}.pkl"
    
    if not os.path.exists(results_file):
        await message.reply_text("❌ No search results found. Please search for an artist first")
        return
    
    with open(results_file, 'rb') as f:
        search_data = pickle.load(f)
    
    videos = search_data['videos']
    query = search_data['query']
    per_page = search_data['per_page']
    
    # Calculate page boundaries
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(videos))
    
    # Build response text
    response = t(
        user_id,
        "found",
        count=len(videos),
        query=query,
        page=page + 1,
        start=start_idx + 1,
        end=end_idx,
    )
    
    # Create inline keyboard buttons
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    buttons = []
    
    # Song buttons (2 columns)
    for i in range(start_idx, end_idx):
        video = videos[i]
        title = video.get('title', 'Unknown')
        duration = video.get('duration', 0)
        
        if duration:
            try:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                duration_str = f"{minutes}:{seconds:02d}"
            except (TypeError, ValueError):
                duration_str = str(duration)
        else:
            duration_str = "Unknown"
        
        # Truncate long titles
        if len(title) > 30:
            title = title[:27] + "..."
        
        button_text = f"{i-start_idx+1}. {title} ({duration_str})"
        buttons.append([InlineKeyboardButton(button_text, callback_data=f"download_{i}")])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page-1}"))
    
    if end_idx < len(videos):
        nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(buttons)

    # If this is called from a callback button, `message` is usually the bot's own message.
    # Editing avoids leaving multiple page messages in chat.
    try:
        if getattr(message.from_user, "is_bot", False):
            await message.edit_text(response, reply_markup=reply_markup)
            return
    except Exception:
        pass

    results_msg = await message.reply_text(response, reply_markup=reply_markup)
    asyncio.create_task(delete_later(results_msg, 90))

async def handle_song_selection(message, song_number: int, user_id: int):
    """Handle song selection and auto-download"""
    import pickle
    import os
    
    results_file = f"search_results_{user_id}.pkl"
    
    if os.path.exists(results_file):
        with open(results_file, 'rb') as f:
            search_data = pickle.load(f)
        
        videos = search_data['videos']
        
        try:
            video_index = song_number - 1
            if 0 <= video_index < len(videos):
                video = videos[video_index]
                video_url = video.get('url')
                title = video.get('title', 'Unknown')
                video_id = video.get('id')
                if not video_id and isinstance(video_url, str):
                    try:
                        from urllib.parse import urlparse, parse_qs
                        parsed = urlparse(video_url)
                        if parsed.hostname in {"youtu.be"}:
                            video_id = parsed.path.lstrip("/")
                        else:
                            qs = parse_qs(parsed.query)
                            video_id = (qs.get("v") or [None])[0]
                    except Exception:
                        video_id = None

                await process_download(message, video_url, title, user_id, video_id)
            else:
                await message.reply_text(f"❌ Invalid number. Please choose 1-{len(videos)}")
        except:
            await message.reply_text("❌ Error processing selection")
    else:
        await message.reply_text("❌ No search results found. Please search for an artist first")

async def process_download(message, video_url: str, title: str, user_id: int, video_id: str | None):
    """Process the actual download"""
    start_msg = await message.reply_text(f"📥 Starting download: {title}\nThis may take a while...")
    
    try:
        import subprocess
        import os
        import glob
        
        # Replit-friendly: download bestaudio without converting to mp3 (ffmpeg often isn't available).
        tmp_dir = os.getenv("TMPDIR") or "/tmp"
        safe_id = video_id or "unknown"
        base_name = f"{user_id}_{safe_id}"
        output_template = f"{tmp_dir}/{base_name}.%(ext)s"
        
        cmd = [
            'yt-dlp',
            '--no-playlist',
            '--retries', '3',
            '--fragment-retries', '3',
            '--socket-timeout', '15',
            '-f', 'bestaudio',
            '-o', output_template,
            video_url
        ]
        
        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        
        if result.returncode == 0:
            matches = glob.glob(f"{tmp_dir}/{base_name}.*")
            downloaded_file = matches[0] if matches else None
            if downloaded_file and os.path.exists(downloaded_file):
                try:
                    with open(downloaded_file, 'rb') as f:
                        await message.reply_audio(audio=f, title=title)
                except Exception as e:
                    logger.error(f"Error sending audio: {e}")
                done_msg = await message.reply_text(f"✅ Download complete: {title}\n📁 File: {downloaded_file}")

                try:
                    os.remove(downloaded_file)
                except Exception:
                    pass

                async def _delete_later(msg, delay: int):
                    try:
                        await asyncio.sleep(delay)
                        await msg.delete()
                    except Exception:
                        pass

                asyncio.create_task(_delete_later(start_msg, 8))
                asyncio.create_task(_delete_later(done_msg, 8))
            else:
                await message.reply_text("✅ Download complete but file not found")
        else:
            await message.reply_text(f"❌ Download failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        await message.reply_text("⏰ Download timed out. Please try again.")
    except Exception as e:
        logger.error(f"Error in download: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

async def photo_command(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Analyze profile photo for authenticity"""
    if not message.photo:
        await message.reply_text("Please send a photo to analyze. Example: /photo (then send image)")
        return
    
    await message.reply_text("🔍 Analyzing photo for authenticity...\nThis may take up to 30 seconds.")
    
    try:
        # Get the largest photo
        photo_file = await message.photo[-1].get_file()
        photo_path = f"temp_photo_{message.from_user.id}.jpg"
        await photo_file.download_to_drive(photo_path)
        
        # For demo: We'll simulate photo analysis
        # In real implementation, you'd use FaceCheck.ID API or reverse image search
        await asyncio.sleep(3)  # Simulate processing time
        
        response = f"📸 **Photo Analysis Results**\n\n"
        
        # Simulated analysis (replace with real API calls)
        response += f"🔍 **Reverse Image Search**:\n"
        response += f"• Found on: 0 other platforms\n"
        response += f"• Stock photo: ❌ Not detected\n"
        response += f"• Multiple profiles: ❌ Not found\n\n"
        
        response += f"🎯 **Authenticity Score**: 85/100\n"
        response += f"• Appears to be original photo\n"
        response += f"• No signs of manipulation\n\n"
        
        response += f"⚠️ **Note**: This is simulated analysis. For production, integrate with:\n"
        response += f"• FaceCheck.ID API\n"
        response += f"• Google Reverse Image Search\n"
        response += f"• TinEye API"
        
        await message.reply_text(response)
        
        # Clean up temp file
        import os
        if os.path.exists(photo_path):
            os.remove(photo_path)
            
    except Exception as e:
        logger.error(f"Error in photo analysis: {e}")
        await message.reply_text(f"❌ Error analyzing photo: {str(e)}")

async def check_command(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await message.reply_text("Please provide a username! Example: /check @user")
        return

    raw = context.args[0].strip()
    username = raw[1:] if raw.startswith("@") else raw

    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", username):
        await message.reply_text("Invalid username format. Example: /check @user")
        return

    await message.reply_text(f"🔍 Investigating: {username}...\nVerifying account existence...")

    try:
        # Verify Telegram and Facebook accounts exist
        telegram_exists = await verify_telegram(username)
        facebook_exists = await verify_facebook(username)
        
        # Run maigret for Instagram verification
        result = subprocess.run(['maigret', '-J', 'simple', '--site', 'Instagram', username], capture_output=True, text=True, timeout=15)
        
        # Build response with verified accounts only
        response = f"🔍 Cross-Platform Analysis: {username}\n\n"
        
        found_count = 0
        
        # Check Telegram
        if telegram_exists:
            response += f"✅ **Telegram**: https://t.me/{username}\n"
            found_count += 1
        else:
            response += f"❌ **Telegram**: Account not found\n"
        
        # Check Instagram via Maigret
        instagram_found = False
        import os
        report_file = f"reports/report_{username}_simple.json"
        
        if os.path.exists(report_file):
            try:
                with open(report_file, 'r') as f:
                    data = json.load(f)
                
                for site_name, site_data in data.items():
                    if 'Instagram' in site_name and isinstance(site_data, dict):
                        status = site_data.get('status', {})
                        if isinstance(status, dict) and status.get('status') == 'Claimed':
                            instagram_found = True
                            response += f"✅ **Instagram**: https://www.instagram.com/{username}/\n"
                            found_count += 1
                            break
            except:
                pass  # JSON parsing failed, continue with direct links
        
        if not instagram_found:
            response += f"❌ **Instagram**: Account not found\n"
        
        # Check Facebook
        if facebook_exists:
            response += f"✅ **Facebook**: https://www.facebook.com/{username}\n"
            found_count += 1
        else:
            response += f"❌ **Facebook**: Account not found\n"
        
        # Analysis
        response += f"\n📊 **Analysis**:\n"
        response += f"• Verified accounts: {found_count}/3 platforms\n"
        
        if found_count == 0:
            response += f"• Status: ❌ No accounts found\n"
        elif found_count == 1:
            response += f"• Status: ⚠️ Single platform presence\n"
        elif found_count == 2:
            response += f"• Status: 🔗 Cross-platform presence (2/3)\n"
        else:
            response += f"• Status: 🎯 Strong cross-platform presence (3/3)\n"
        
        response += f"• Username consistency: {username} across all checked platforms"
        
        await message.reply_text(response)
            
    except subprocess.TimeoutExpired:
        await message.reply_text("⏰ Search timed out. Please try again.")
    except Exception as e:
        logger.error(f"Error in maigret search: {e}")
        await message.reply_text(f"❌ Error: {str(e)}")

async def handle_button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Acknowledge the button click
    await query.answer()
    
    if query.data.startswith("download_"):
        # Extract song index
        song_index = int(query.data.split("_")[1])
        await handle_song_selection(query.message, song_index + 1, user_id)  # +1 because handle expects 1-based
        asyncio.create_task(delete_later(query.message, 3))
        
    elif query.data.startswith("page_"):
        # Extract page number
        page = int(query.data.split("_")[1])
        await show_songs_page(query.message, user_id, page)

    elif query.data.startswith("lang_"):
        lang = query.data.split("_", 1)[1]
        set_user_lang(user_id, lang)
        try:
            await query.edit_message_text(t(user_id, "lang_set"))
            asyncio.create_task(delete_later(query.message, 4))
        except Exception:
            pass

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - either song selection or echo"""
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    urls = extract_urls(text)
    if urls:
        url = urls[0]
        if is_youtube_url(url) or is_instagram_url(url):
            await handle_video_link(update.message, url, user_id)
            return
    
    # Check if it's a song selection (single number)
    if text.isdigit() and len(text) <= 2:
        # User is selecting a song to download
        await handle_song_selection(update.message, int(text), user_id)
    else:
        # Check if it looks like an artist/song search (not a command)
        if not text.startswith('/') and len(text.split()) >= 1:
            # Treat as music search
            await search_songs(update.message, text, user_id)
        else:
            # Echo the message
            await update.message.reply_text(f"You said: {update.message.text}")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(f"You said: {update.message.text}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main() -> None:
    """Start the bot."""
    # Validate configuration
    Config.validate()
    
    # Create the Application
    # Replit can be slow to upload larger audio files; increase request timeouts.
    from telegram.request import HTTPXRequest
    request = HTTPXRequest(
        connect_timeout=30,
        read_timeout=300,
        write_timeout=300,
        pool_timeout=30,
    )
    application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).request(request).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("photo", photo_command))
    application.add_handler(CommandHandler("music", handle_music_search))

    # Add callback query handler for inline buttons
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_button_click))

    # Add message handler for text messages (including song selection numbers)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    logger.info(f"Starting {Config.BOT_NAME} bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
