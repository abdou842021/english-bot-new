import os
import json
import tempfile

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from deep_translator import GoogleTranslator
import edge_tts

import eng_to_ipa as ipa
from PyDictionary import PyDictionary
from PIL import Image
import pytesseract


# ==================================================
# الإعدادات
# ==================================================

TOKEN = os.getenv("BOT_TOKEN")

# ضع رقم حسابك في Railway لاحقًا كـ OWNER_ID
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

ALLOWED_GROUPS_FILE = "allowed_groups.json"


# ==================================================
# تحميل وحفظ المجموعات
# ==================================================

def load_allowed_groups():
    if os.path.exists(ALLOWED_GROUPS_FILE):
        try:
            with open(ALLOWED_GROUPS_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()

    return set()


def save_allowed_groups(groups):
    with open(ALLOWED_GROUPS_FILE, "w", encoding="utf-8") as f:
        json.dump(list(groups), f)


allowed_groups = load_allowed_groups()


# ==================================================
# الأدوات
# ==================================================

tool = language_tool_python.LanguageTool("en-US")
dictionary = PyDictionary()


# ==================================================
# دوال مساعدة
# ==================================================

async def generate_voice(text: str, voice: str) -> str:
    communicate = edge_tts.Communicate(text, voice)

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    ) as f:
        await communicate.save(f.name)
        return f.name


def is_long_text(text: str) -> bool:
    return len(text.split()) > 8


def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if (
        update.message
        and update.message.reply_to_message
        and update.message.reply_to_message.text
    ):
        return update.message.reply_to_message.text.strip()

    if context.args:
        return " ".join(context.args).strip()

    return None


def is_allowed(update: Update) -> bool:
    if not update.effective_chat:
        return False

    # المالك يستطيع استعمال البوت
    if is_owner(update):
        return True

    # الخاص مسموح للمالك فقط
    if update.effective_chat.type == "private":
        return False

    return update.effective_chat.id in allowed_groups


def is_owner(update: Update) -> bool:
    if not update.effective_user:
        return False

    return update.effective_user.id == OWNER_ID


# ==================================================
# أوامر الإدارة
# ==================================================

async def add_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        await update.message.reply_text(
            "⛔ هذا الأمر خاص بالمالك فقط."
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
                "❌ رقم المجموعة غير صحيح."
            )
            return

    if not group_id:
        await update.message.reply_text(
            "استعمل الأمر هكذا:\n\n"
            "1️⃣ رد على أي رسالة من المجموعة واكتب /اضف\n"
            "2️⃣ أو اكتب:\n"
            "/اضف -1001234567890"
        )
        return

    allowed_groups.add(group_id)
    save_allowed_groups(allowed_groups)

    await update.message.reply_text(
        f"✅ تمت إضافة المجموعة:\n`{group_id}`",
        parse_mode="Markdown"
    )


async def remove_group(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        await update.message.reply_text(
            "⛔ هذا الأمر خاص بالمالك فقط."
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
                "❌ رقم المجموعة غير صحيح."
            )
            return

    if not group_id:
        await update.message.reply_text(
            "رد على رسالة من المجموعة أو أعطني رقمها."
        )
        return

    if group_id in allowed_groups:

        allowed_groups.remove(group_id)
        save_allowed_groups(allowed_groups)

        await update.message.reply_text(
            f"❌ تم منع المجموعة:\n`{group_id}`",
            parse_mode="Markdown"
        )

    else:
        await update.message.reply_text(
            "ℹ️ هذه المجموعة غير موجودة أصلًا في القائمة."
        )


async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        await update.message.reply_text(
            "⛔ هذا الأمر خاص بالمالك فقط."
        )
        return

    if not allowed_groups:
        await update.message.reply_text(
            "📭 لا توجد أي مجموعة مسموح بها حاليًا."
        )
        return

    text = "📋 المجموعات المسموح بها:\n\n"

    for group_id in allowed_groups:
        text += f"`{group_id}`\n"

    await update.message.reply_text(
        text,
        parse_mode="Markdown"
    )


# ==================================================
# /start
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_allowed(update):
        return

    await update.message.reply_text(
        "السلام عليكم 👋\n\n"
        "🤖 مرحبًا بك في بوت تعلم الإنجليزية!\n\n"
        "الأوامر المتوفرة:\n"
        "🌍 /ترجم\n"
        "🇬🇧 /انطق\n"
        "🇺🇸 /انطق_امريكي\n"
        "✍️ /صحح\n"
        "📖 /اشرح\n"
        "📷 /حول\n\n"
        "أوامر الإدارة للمالك فقط:\n"
        "➕ /اضف\n"
        "➖ /منع\n"
        "📋 /المجموعات"
    )


# ==================================================
# الترجمة
# ==================================================

async def translate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "استعمل:\n/ترجم hello\n\n"
            "أو رد على رسالة واكتب /ترجم"
        )
        return

    try:
        arabic = GoogleTranslator(
            source="en",
            target="ar"
        ).translate(text)

        phonetic = ipa.convert(text)

        await update.message.reply_text(
            f"🇬🇧 {text}\n"
            f"🇩🇿 {arabic}\n"
            f"🔤 {phonetic}"
        )

    except Exception as e:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء الترجمة."
        )


# ==================================================
# النطق البريطاني
# ==================================================

async def pronounce_british(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "استعمل:\n/انطق hello\n\n"
            "أو رد على رسالة واكتب /انطق"
        )
        return

    voice = "en-GB-SoniaNeural"
    audio_path = None

    try:

        audio_path = await generate_voice(
            text,
            voice
        )

        if is_long_text(text):

            with open(audio_path, "rb") as audio:
                await update.message.reply_voice(
                    voice=audio
                )

        else:

            phonetic = ipa.convert(text)

            with open(audio_path, "rb") as audio:
                await update.message.reply_voice(
                    voice=audio,
                    caption=f"🇬🇧 British\n🔤 {phonetic}"
                )

    except Exception:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء إنشاء النطق."
        )

    finally:

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# ==================================================
# النطق الأمريكي
# ==================================================

async def pronounce_american(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "استعمل:\n/انطق_امريكي hello\n\n"
            "أو رد على رسالة واكتب /انطق_امريكي"
        )
        return

    voice = "en-US-JennyNeural"
    audio_path = None

    try:

        audio_path = await generate_voice(
            text,
            voice
        )

        if is_long_text(text):

            with open(audio_path, "rb") as audio:
                await update.message.reply_voice(
                    voice=audio
                )

        else:

            phonetic = ipa.convert(text)

            with open(audio_path, "rb") as audio:
                await update.message.reply_voice(
                    voice=audio,
                    caption=f"🇺🇸 American\n🔤 {phonetic}"
                )

    except Exception:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء إنشاء النطق."
        )

    finally:

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# ==================================================
# تصحيح الإنجليزية
# ==================================================

async def correct_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "استعمل:\n"
            "/صحح I has a book\n\n"
            "أو رد على رسالة واكتب /صحح"
        )
        return

    try:

        corrected = tool.correct(text)

        if corrected.lower() == text.lower():

            await update.message.reply_text(
                "✅ النص صحيح."
            )

        else:

            await update.message.reply_text(
                f"❌ الأصل:\n{text}\n\n"
                f"✅ التصحيح:\n{corrected}"
            )

    except Exception:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء التصحيح."
        )


# ==================================================
# شرح / مرادفات
# ==================================================

async def explain_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "استعمل:\n/اشرح happy"
        )
        return

    word = text.split()[0]

    try:

        synonyms = dictionary.synonym(word)

        if synonyms:

            words = synonyms[:8]

            await update.message.reply_text(
                f"📖 مرادفات {word}:\n"
                + "، ".join(words)
            )

        else:

            await update.message.reply_text(
                f"لم أجد مرادفات لـ {word}."
            )

    except Exception:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء البحث."
        )


# ==================================================
# استخراج النص من الصورة OCR
# ==================================================

async def ocr_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_allowed(update):
        return

    photo = None

    # إذا كان الأمر ردًا على صورة
    if (
        update.message.reply_to_message
        and update.message.reply_to_message.photo
    ):
        photo = update.message.reply_to_message.photo[-1]

    # إذا أرسل صورة ومعها /حول
    elif update.message.photo:
        photo = update.message.photo[-1]

    if not photo:

        await update.message.reply_text(
            "📷 رد على صورة بـ /حول\n"
            "أو أرسل صورة ومعها /حول"
        )
        return

    image_path = None

    try:

        telegram_file = await context.bot.get_file(
            photo.file_id
        )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        ) as f:

            image_path = f.name

        await telegram_file.download_to_drive(
            image_path
        )

        image = Image.open(image_path)

        text = pytesseract.image_to_string(
            image,
            lang="eng"
        ).strip()

        if text:

            await update.message.reply_text(
                f"📄 النص المستخرج من الصورة:\n\n{text}"
            )

        else:

            await update.message.reply_text(
                "❌ لم أستطع العثور على نص واضح في الصورة."
            )

    except Exception:
        await update.message.reply_text(
            "❌ حدث خطأ أثناء قراءة الصورة."
        )

    finally:

        if image_path and os.path.exists(image_path):
            os.remove(image_path)


# ==================================================
# تشغيل البوت
# ==================================================

def main():

    if not TOKEN:
        raise RuntimeError(
            "BOT_TOKEN غير موجود في Environment Variables."
        )

    app = Application.builder().token(TOKEN).build()

    # الأوامر العادية
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        CommandHandler("ترجم", translate_cmd)
    )

    app.add_handler(
        CommandHandler("انطق", pronounce_british)
    )

    app.add_handler(
        CommandHandler(
            "انطق_امريكي",
            pronounce_american
        )
    )

    app.add_handler(
        CommandHandler("صحح", correct_cmd)
    )

    app.add_handler(
        CommandHandler("اشرح", explain_cmd)
    )

    app.add_handler(
        CommandHandler("حول", ocr_cmd)
    )

    # أوامر الإدارة
    app.add_handler(
        CommandHandler("اضف", add_group)
    )

    app.add_handler(
        CommandHandler("منع", remove_group)
    )

    app.add_handler(
        CommandHandler("المجموعات", list_groups)
    )

    # صورة مع /حول في الكابشن
    app.add_handler(
        MessageHandler(
            filters.PHOTO
            & filters.CaptionRegex(r"^/حول"),
            ocr_cmd
        )
    )

    print("🤖 البوت خدام...")

    app.run_polling()


if __name__ == "__main__":
    main()
