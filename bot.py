import os
import json
import tempfile
import urllib.parse
import urllib.request

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from deep_translator import GoogleTranslator
import edge_tts
import eng_to_ipa as ipa


# ==================================================
# الإعدادات
# ==================================================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

GROUPS_FILE = "allowed_groups.json"


# ==================================================
# المجموعات المسموح بها
# ==================================================

def load_groups():
    if not os.path.exists(GROUPS_FILE):
        return set()

    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return set(int(x) for x in data)

    except Exception:
        return set()


def save_groups():
    with open(GROUPS_FILE, "w", encoding="utf-8") as file:
        json.dump(list(allowed_groups), file)


allowed_groups = load_groups()


# ==================================================
# أدوات مساعدة
# ==================================================

def is_owner(update: Update):
    if not update.effective_user:
        return False

    return update.effective_user.id == OWNER_ID


def is_allowed(update: Update):

    if not update.effective_chat:
        return False

    if is_owner(update):
        return True

    if update.effective_chat.type == "private":
        return False

    return update.effective_chat.id in allowed_groups


def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # إذا كان الأمر ردًا على رسالة
    if (
        update.message
        and update.message.reply_to_message
        and update.message.reply_to_message.text
    ):
        return update.message.reply_to_message.text.strip()

    # إذا كان النص بعد الأمر
    if context.args:
        return " ".join(context.args).strip()

    return None


async def make_voice(text, voice):

    file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp3"
    )

    file.close()

    communicate = edge_tts.Communicate(
        text,
        voice
    )

    await communicate.save(file.name)

    return file.name


# ==================================================
# /start
# ==================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_allowed(update):
        return

    await update.message.reply_text(
        "السلام عليكم 👋\n\n"
        "🤖 مرحبًا بك في بوت تعلم الإنجليزية!\n\n"
        "الأوامر:\n\n"
        "🌍 /ترجم\n"
        "🇬🇧 /انطق\n"
        "🇺🇸 /انطق_امريكي\n"
        "✍️ /صحح\n"
        "📖 /اشرح\n"
        "📷 /حول\n\n"
        "أوامر المالك:\n"
        "➕ /اضف\n"
        "➖ /منع\n"
        "📋 /المجموعات"
    )


# ==================================================
# /ترجم
# ==================================================

async def translate_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_allowed(update):
        return

    text = get_text(update, context)

    if not text:
        await update.message.reply_text(
            "استعمل:\n\n"
            "/ترجم hello\n\n"
            "أو رد على رسالة واكتب /ترجم"
        )
        return

    try:

        arabic = GoogleTranslator(
            source="en",
            target="ar"
        ).translate(text)

        try:
            phonetic = ipa.convert(text)
        except Exception:
            phonetic = "غير متوفر"

        await update.message.reply_text(
            f"🇬🇧 {text}\n\n"
            f"🇩🇿 {arabic}\n\n"
            f"🔤 {phonetic}"
        )

    except Exception as error:

        print("Translation error:", error)

        await update.message.reply_text(
            "❌ حدث خطأ أثناء الترجمة.\n"
            "حاول مرة أخرى."
        )


# ==================================================
# /انطق
# British
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
            "استعمل:\n\n"
            "/انطق hello\n\n"
            "أو رد على رسالة واكتب /انطق"
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
            phonetic = "غير متوفر"

        with open(audio_path, "rb") as audio:

            await update.message.reply_voice(
                voice=audio,
                caption=f"🇬🇧 British\n🔤 {phonetic}"
            )

    except Exception as error:

        print("British voice error:", error)

        await update.message.reply_text(
            "❌ حدث خطأ أثناء إنشاء النطق."
        )

    finally:

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# ==================================================
# /انطق_امريكي
# American
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
            "استعمل:\n\n"
            "/انطق_امريكي hello\n\n"
            "أو رد على رسالة واكتب /انطق_امريكي"
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
            phonetic = "غير متوفر"

        with open(audio_path, "rb") as audio:

            await update.message.reply_voice(
                voice=audio,
                caption=f"🇺🇸 American\n🔤 {phonetic}"
            )

    except Exception as error:

        print("American voice error:", error)

        await update.message.reply_text(
            "❌ حدث خطأ أثناء إنشاء النطق."
        )

    finally:

        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)


# ==================================================
# /صحح
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
            "استعمل:\n\n"
            "/صحح I has a book\n\n"
            "أو رد على رسالة واكتب /صحح"
        )
        return

    # تصحيحات بسيطة وآمنة بدون Java أو LanguageTool
    corrections = {
        "i has": "I have",
        "i have went": "I have gone",
        "he have": "he has",
        "she have": "she has",
        "they was": "they were",
        "we was": "we were",
        "i is": "I am",
        "he are": "he is",
        "she are": "she is",
        "you is": "you are",
        "it are": "it is",
        "there is many": "there are many",
        "there is some": "there are some",
        "i am agree": "I agree",
        "he don't": "he doesn't",
        "she don't": "she doesn't",
        "it don't": "it doesn't",
        "he do": "he does",
        "she do": "she does",
    }

    corrected = text

    lower_text = corrected.lower()

    for wrong, right in corrections.items():

        if wrong in lower_text:

            index = lower_text.find(wrong)

            corrected = (
                corrected[:index]
                + right
                + corrected[index + len(wrong):]
            )

            lower_text = corrected.lower()

    if corrected == text:

        await update.message.reply_text(
            "✅ لم أجد خطأ واضحًا في الجملة."
        )

    else:

        await update.message.reply_text(
            f"❌ الأصل:\n{text}\n\n"
            f"✅ التصحيح:\n{corrected}"
        )


# ==================================================
# /اشرح
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
            "استعمل:\n\n"
            "/اشرح benefit"
        )
        return

    word = text.split()[0]

    try:

        arabic = GoogleTranslator(
            source="en",
            target="ar"
        ).translate(word)

        phonetic = ipa.convert(word)

    except Exception:

        arabic = "غير متوفر"
        phonetic = "غير متوفر"

    await update.message.reply_text(
        f"📖 الكلمة: {word}\n\n"
        f"🇩🇿 المعنى: {arabic}\n"
        f"🔤 النطق: {phonetic}\n\n"
        f"💡 يمكنك استعمال /ترجم و /انطق "
        f"للحصول على ترجمة ونطق أكثر."
    )


# ==================================================
# /حول
# ==================================================

async def ocr_cmd(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_allowed(update):
        return

    await update.message.reply_text(
        "📷 ميزة استخراج النص من الصور قيد التجهيز.\n\n"
        "سنضيفها بعد ما نتأكد أن النسخة الأساسية من البوت تعمل بدون مشاكل."
    )


# ==================================================
# /اضف
# ==================================================

async def add_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await update.message.reply_text(
            "⛔ هذا الأمر خاص بالمالك فقط."
        )
        return

    group_id = None

    # إذا كان ردًا على رسالة داخل المجموعة
    if update.message.reply_to_message:

        group_id = update.message.reply_to_message.chat.id

    # أو كتابة ID المجموعة
    elif context.args:

        try:
            group_id = int(context.args[0])

        except ValueError:

            await update.message.reply_text(
                "❌ رقم المجموعة غير صحيح."
            )
            return

    if group_id is None:

        await update.message.reply_text(
            "استعمل:\n\n"
            "1️⃣ رد على رسالة من المجموعة واكتب /اضف\n\n"
            "أو:\n"
            "/اضف -1001234567890"
        )
        return

    allowed_groups.add(group_id)

    save_groups()

    await update.message.reply_text(
        f"✅ تمت إضافة المجموعة.\n\n"
        f"ID: `{group_id}`",
        parse_mode="Markdown"
    )


# ==================================================
# /منع
# ==================================================

async def remove_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

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

    if group_id is None:

        await update.message.reply_text(
            "رد على رسالة من المجموعة واكتب /منع\n"
            "أو اكتب رقم المجموعة."
        )
        return

    if group_id in allowed_groups:

        allowed_groups.remove(group_id)

        save_groups()

        await update.message.reply_text(
            f"❌ تم منع المجموعة.\n\n"
            f"ID: `{group_id}`",
            parse_mode="Markdown"
        )

    else:

        await update.message.reply_text(
            "ℹ️ هذه المجموعة غير موجودة في القائمة."
        )


# ==================================================
# /المجموعات
# ==================================================

async def list_groups(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    if not is_owner(update):

        await update.message.reply_text(
            "⛔ هذا الأمر خاص بالمالك فقط."
        )
        return

    if not allowed_groups:

        await update.message.reply_text(
            "📭 لا توجد مجموعات مسموح بها."
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
# تشغيل البوت
# ==================================================

def main():

    if not TOKEN:

        raise RuntimeError(
            "❌ BOT_TOKEN غير موجود."
        )

    if OWNER_ID == 0:

        raise RuntimeError(
            "❌ OWNER_ID غير موجود."
        )

    application = (
        Application
        .builder()
        .token(TOKEN)
        .build()
    )

    # الأوامر
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("ترجم", translate_cmd)
    )

    application.add_handler(
        CommandHandler("انطق", pronounce_british)
    )

    application.add_handler(
        CommandHandler(
            "انطق_امريكي",
            pronounce_american
        )
    )

    application.add_handler(
        CommandHandler("صحح", correct_cmd)
    )

    application.add_handler(
        CommandHandler("اشرح", explain_cmd)
    )

    application.add_handler(
        CommandHandler("حول", ocr_cmd)
    )

    application.add_handler(
        CommandHandler("اضف", add_group)
    )

    application.add_handler(
        CommandHandler("منع", remove_group)
    )

    application.add_handler(
        CommandHandler(
            "المجموعات",
            list_groups
        )
    )

    print("🤖 البوت يعمل الآن...")

    application.run_polling(
        drop_pending_updates=True
    )


# ==================================================
# البداية
# ==================================================

if __name__ == "__main__":
    main()
