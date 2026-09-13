import os
import json
import tempfile
from flask import Flask
from threading import Thread

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from deep_translator import GoogleTranslator
import edge_tts
import eng_to_ipa as ipa

import argostranslate.package
import argostranslate.translate

def install_translation_model():
    try:
        argostranslate.package.update_package_index()
        packages = argostranslate.package.get_available_packages()

        for package in packages:
            if package.from_code == "en" and package.to_code == "ar":
                package.install()
                print("✅ English → Arabic model installed.")
                return

        print("❌ English → Arabic model not found.")

    except Exception as e:
        print("❌ Translation model error:", e)

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

GROUPS_FILE = "allowed_groups.json"


def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return set()

    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_groups():
    try:
        with open(GROUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(list(allowed_groups), f)
    except Exception as e:
        print("Save groups error:", e)


allowed_groups = load_groups()
web_app = Flask(__name__)

@web_app.route("/")
def home():
    return "Bot is alive!"

def run_web():
    port = int(os.getenv("PORT", "10000"))
    web_app.run(host="0.0.0.0", port=port)

def is_owner(update):
    return (
        update.effective_user is not None
        and update.effective_user.id == OWNER_ID
    )


def is_allowed(update):
    if not update.effective_chat:
        return False

    if is_owner(update):
        return True

    if update.effective_chat.type == "private":
        return False

    return update.effective_chat.id in allowed_groups


def get_text(update, context):
    if (
        update.message
        and update.message.reply_to_message
        and update.message.reply_to_message.text
    ):
        return update.message.reply_to_message.text.strip()

    if context.args:
        return " ".join(context.args).strip()

    return None


async def make_voice(text, voice):
    file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )
    file.close()

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(file.name)

    return file.name


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update):
        return

    await update.message.reply_text(
        "🤖 English Learning Bot\n\n"
        "Commands:\n"
        "/tr - Translate\n"
        "/pr - British pronunciation\n"
        "/prus - American pronunciation\n"
        "/cor - Correct\n"
        "/ex - Explain\n"
        "/ocr - Image to text\n\n"
        "Owner:\n"
        "/add - Add group\n"
        "/del - Remove group\n"
        "/list - List groups"
    )


# =========================
# TRANSLATE
# =========================


async def translate_cmd(update, context):
    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "Use:\n/tr hello\n\n"
            "Or reply to a message with /tr"
        )
        return

    try:
        arabic = GoogleTranslator(
            source="en",
            target="ar"
        ).translate(text)

        await update.message.reply_text(
            f"🇬🇧 {text}\n\n"
            f"🇩🇿 {arabic}"
        )

    except Exception as e:
        print("Translate error:", e)
        await update.message.reply_text(
            "❌ Translation failed."
        )

# =========================
# BRITISH
# =========================

async def pronounce_british(update, context):
    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "Use:\n/pr hello"
        )
        return

    audio_path = None

    try:
        audio_path = await make_voice(
            text,
            "en-GB-SoniaNeural"
        )

        try:
            phonetic = ipa.convert(text)
        except Exception:
            phonetic = "N/A"

        with open(audio_path, "rb") as audio:
            await update.message.reply_voice(
                voice=audio,
                caption=f"🇬🇧 British\n🔤 {phonetic}"
            )

    except Exception as e:
        print("British error:", e)
        await update.message.reply_text(
            "❌ Pronunciation failed."
        )

    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# =========================
# AMERICAN
# =========================

async def pronounce_american(update, context):
    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "Use:\n/prus hello"
        )
        return

    audio_path = None

    try:
        audio_path = await make_voice(
            text,
            "en-US-JennyNeural"
        )

        try:
            phonetic = ipa.convert(text)
        except Exception:
            phonetic = "N/A"

        with open(audio_path, "rb") as audio:
            await update.message.reply_voice(
                voice=audio,
                caption=f"🇺🇸 American\n🔤 {phonetic}"
            )

    except Exception as e:
        print("American error:", e)
        await update.message.reply_text(
            "❌ Pronunciation failed."
        )

    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# =========================
# CORRECT
# =========================

async def correct_cmd(update, context):
    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "Use:\n/cor I has a book"
        )
        return

    corrections = {
        "i has": "I have",
        "he have": "he has",
        "she have": "she has",
        "they was": "they were",
        "we was": "we were",
        "i is": "I am",
        "he are": "he is",
        "she are": "she is",
        "you is": "you are",
        "it are": "it is",
        "i am agree": "I agree",
        "he don't": "he doesn't",
        "she don't": "she doesn't",
        "it don't": "it doesn't",
        "he do": "he does",
        "she do": "she does",
    }

    corrected = text
    lower = corrected.lower()

    for wrong, right in corrections.items():
        if wrong in lower:
            index = lower.find(wrong)

            corrected = (
                corrected[:index]
                + right
                + corrected[index + len(wrong):]
            )

            lower = corrected.lower()

    if corrected == text:
        await update.message.reply_text(
            "✅ No obvious mistake found."
        )
    else:
        await update.message.reply_text(
            f"❌ Original:\n{text}\n\n"
            f"✅ Corrected:\n{corrected}"
        )


# =========================
# EXPLAIN
# =========================

async def explain_cmd(update, context):
    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "Use:\n/ex benefit"
        )
        return

    word = text.split()[0]

    try:
        meaning = GoogleTranslator(
            source="en",
            target="ar"
        ).translate(word)

        phonetic = ipa.convert(word)

        await update.message.reply_text(
            f"📖 {word}\n\n"
            f"🇩🇿 {meaning}\n"
            f"🔤 {phonetic}"
        )

    except Exception as e:
        print("Explain error:", e)
        await update.message.reply_text(
            "❌ Explanation failed."
        )


# =========================
# OCR
# =========================

async def ocr_cmd(update, context):
    if not is_allowed(update):
        return

    await update.message.reply_text(
        "📷 OCR is not active yet."
    )


# =========================
# ADD GROUP
# =========================

async def add_group(update, context):
    if not is_owner(update):
        await update.message.reply_text(
            "⛔ Owner only."
        )
        return
    group_id = None

    if update.effective_chat and update.effective_chat.type != "private":
        group_id = update.effective_chat.id

    elif context.args:

        try:
            group_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid group ID."
            )
            return

    if group_id is None:
        await update.message.reply_text(
            "Reply to a group message with /add\n"
            "or use /add GROUP_ID"
        )
        return

    allowed_groups.add(group_id)
    save_groups()

    await update.message.reply_text(
        f"✅ Group added.\nID: {group_id}"
    )


# =========================
# DELETE GROUP
# =========================

async def delete_group(update, context):
    if not is_owner(update):
        await update.message.reply_text(
            "⛔ Owner only."
        )
        return

    group_id = None

    if update.message.reply_to_message:
        group_id = update.message.reply_to_message.chat.id

    elif context.args:
        try:
            group_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid group ID."
            )
            return

    if group_id is None:
        await update.message.reply_text(
            "Reply to a group message with /del\n"
            "or use /del GROUP_ID"
        )
        return

    if group_id in allowed_groups:
        allowed_groups.remove(group_id)
        save_groups()

        await update.message.reply_text(
            f"❌ Group removed.\nID: {group_id}"
        )
    else:
        await update.message.reply_text(
            "ℹ️ Group is not in the list."
        )


# =========================
# LIST GROUPS
# =========================

async def list_groups(update, context):
    if not is_owner(update):
        await update.message.reply_text(
            "⛔ Owner only."
        )
        return

    if not allowed_groups:
        await update.message.reply_text(
            "📭 No groups."
        )
        return

    text = "📋 Groups:\n\n"

    for group_id in sorted(allowed_groups):
        text += f"{group_id}\n"

    await update.message.reply_text(text)


# =========================
# MAIN
# =========================

def main():
    install_translation_model()

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing."
        )

    if OWNER_ID == 0:
        raise RuntimeError(
            "OWNER_ID is missing."
        )

    app = (
        Application.builder()
        .token(TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tr", translate_cmd))
    app.add_handler(CommandHandler("pr", pronounce_british))
    app.add_handler(CommandHandler("prus", pronounce_american))
    app.add_handler(CommandHandler("cor", correct_cmd))
    app.add_handler(CommandHandler("ex", explain_cmd))
    app.add_handler(CommandHandler("ocr", ocr_cmd))

    app.add_handler(CommandHandler("add", add_group))
    app.add_handler(CommandHandler("del", delete_group))
    app.add_handler(CommandHandler("list", list_groups))

    print("🤖 BOT IS RUNNING")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    main()
