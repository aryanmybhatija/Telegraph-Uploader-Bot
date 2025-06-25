import os
import logging
import requests
import mimetypes
import json
from threading import Thread
from flask import Flask
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ParseMode, MessageMediaType
from PIL import Image

# ============================ #
# 🔐 Environment Config Setup  #
# ============================ #
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
TELEGRAPH_ACCESS_TOKEN = os.environ.get("TELEGRAPH_ACCESS_TOKEN", "")

# ====================== #
# ✅ Logging Setup       #
# ====================== #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AngelBot")

# ====================== #
# 🌐 Flask for keepalive #
# ====================== #
app = Flask(__name__)
@app.route('/')
def home():
    return "✅ AngelBot is running"

Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()

# ====================== #
# 🤖 Pyrogram Bot Setup  #
# ====================== #
angelbot = Client(
    "angelbot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

# ====================== #
# ⚙️ Configuration       #
# ====================== #
LIMIT = 5 * 1024 * 1024  # 5MB
DOWNLOAD_DIR = "./Downloads"
SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
TELEGRAPH_UPLOAD_URL = "https://telegra.ph/upload"
TELEGRAPH_API_URL = "https://api.telegra.ph/createPage"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

START_IMAGE_URL = "https://i.ibb.co/j9n6nZxD/Op-log.png"
START_TEXT = """
🌟 **Hello {user_name}!**

I'm **AngelBot Telegraph Uploader** 🤖  
I'll upload any image to Telegraph and give you the link!

📁 **Supported Formats:**
```{formats}```
📏 **Size Limit:** `{limit}MB`

⚡️ **Developer:** @Opleech_WD
"""

HELP_TEXT = """
ℹ️ **Bot Usage Guide:**

1. Send me any image
2. Add a caption for the image (optional)
3. I'll automatically upload it to Telegraph
4. You'll receive the download link

📌 **Supported Formats:**
{formats}

📏 **Maximum Size:** {limit}MB
"""

def upload_to_telegraph(file_path):
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type or not mime_type.startswith("image"):
            mime_type = "image/jpeg"
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, mime_type)
            }
            headers = {
                'User-Agent': 'Mozilla/5.0'
            }
            response = requests.post(
                TELEGRAPH_UPLOAD_URL,
                files=files,
                headers=headers,
                timeout=30
            )
        if response.status_code != 200:
            raise Exception(f"API returned status: {response.status_code}, Response: {response.text}")
        result = response.json()
        logger.info(f"Telegraph response: {result}")
        if isinstance(result, list) and result and 'src' in result[0]:
            return f"https://telegra.ph{result[0]['src']}"
        elif 'error' in result:
            raise Exception(result['error'])
        raise Exception(f"Unexpected API response: {response.text}")
    except Exception as e:
        logger.error(f"Telegraph upload error: {e}")
        raise Exception(f"Telegraph upload failed: {str(e)}")

def create_telegraph_page(title, content_html):
    data = {
        "title": title[:256],
        "author_name": "AngelBot",
        "author_url": "https://t.me/Opleech_WD",
        "return_content": False
    }
    if TELEGRAPH_ACCESS_TOKEN:
        data["access_token"] = TELEGRAPH_ACCESS_TOKEN
    if isinstance(content_html, list):
        data["content"] = json.dumps(content_html)
    else:
        data["content"] = content_html
    response = requests.post(TELEGRAPH_API_URL, data=data)
    result = response.json()
    if result.get("ok"):
        return result["result"]["url"]
    else:
        raise Exception(f"Telegraph error: {result.get('error', 'Unknown error')}")

def generate_page_with_image(image_url, description, title="📸 Uploaded Image"):
    content_html = [
        {
            "tag": "figure",
            "children": [
                {"tag": "img", "attrs": {"src": image_url}},
                {"tag": "figcaption", "children": [description[:512]]}
            ]
        }
    ]
    return create_telegraph_page(title, content_html)

def optimize_image(file_path):
    try:
        if os.path.getsize(file_path) > 2 * 1024 * 1024:
            with Image.open(file_path) as img:
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                if img.width > 1280:
                    new_height = int(1280 * img.height / img.width)
                    img = img.resize((1280, new_height), Image.LANCZOS)
                optimized_path = os.path.splitext(file_path)[0] + "_optimized.jpg"
                img.save(optimized_path, "JPEG", optimize=True, quality=85)
                os.remove(file_path)
                return optimized_path
        return file_path
    except Exception as e:
        logger.error(f"Image optimization error: {e}")
        return file_path

@angelbot.on_message(filters.command(["start"]) & filters.private)
async def start(_, message):
    try:
        await message.reply_photo(
            photo=START_IMAGE_URL,
            caption=START_TEXT.format(
                user_name=message.from_user.first_name,
                formats=", ".join(SUPPORTED_FORMATS),
                limit=LIMIT//(1024*1024)
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 Update Channel", url="https://t.me/Opleech_WD"),
                 InlineKeyboardButton("💬 Support Group", url="https://t.me/Opleech_WD")],
                [InlineKeyboardButton("ℹ️ Help", callback_data="help"),
                 InlineKeyboardButton("✨ Premium", url="https://t.me/Opleech_WD")]
            ])
        )
    except Exception as e:
        logger.error(f"Start error: {e}")
        await message.reply_text(
            text=START_TEXT.format(
                user_name=message.from_user.first_name,
                formats=", ".join(SUPPORTED_FORMATS),
                limit=LIMIT//(1024*1024)
            ),
            parse_mode=ParseMode.MARKDOWN
        )

@angelbot.on_message(filters.command(["help"]) & filters.private)
async def help_command(_, message):
    await message.reply_text(
        text=HELP_TEXT.format(
            formats="\n".join([f"• `{fmt}`" for fmt in SUPPORTED_FORMATS]),
            limit=LIMIT//(1024*1024)
        ),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

@angelbot.on_callback_query(filters.regex("^help$"))
async def help_callback(_, query):
    await query.answer()
    await query.message.reply_text(
        text=HELP_TEXT.format(
            formats="\n".join([f"• `{fmt}`" for fmt in SUPPORTED_FORMATS]),
            limit=LIMIT//(1024*1024)
        ),
        parse_mode=ParseMode.MARKDOWN,
        disable_web_page_preview=True
    )

@angelbot.on_message(filters.private & (filters.photo | filters.document))
async def handle_media(_, message):
    try:
        if message.media == MessageMediaType.PHOTO:
            file_size = message.photo.file_size
            file_ext = ".jpg"
            caption = message.caption or "Uploaded by AngelBot"
        elif message.media == MessageMediaType.DOCUMENT:
            file_size = message.document.file_size
            file_name = message.document.file_name or ""
            file_ext = os.path.splitext(file_name)[1].lower()
            caption = message.caption or "Uploaded by AngelBot"
        else:
            return

        if file_size > LIMIT:
            return await message.reply_text(
                f"❌ File size too
