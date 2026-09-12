import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from deep_translator import GoogleTranslator
from gtts import gTTS

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "Send me an English word or sentence, and I'll give you:\n"
        "🇩🇿 Arabic translation\n"
        "🔊 Pronunciation"
    )

async def translate_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if not text:
        return

    try:
        translation = GoogleTranslator(
            source="auto",
            target="ar"
        ).translate(text)

        await update.message.reply_text(
            f"🇩🇿 الترجمة: {translation}\n"
            f"🔤 الكلمة: {text}"
        )

        audio_file = "pronunciation.mp3"
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(audio_file)

        with open(audio_file, "rb") as audio:
            await update.message.reply_voice(voice=audio)

        os.remove(audio_file)

    except Exception as e:
        await update.message.reply_text(
            "❌ حدث خطأ، حاول مرة أخرى."
        )

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, translate_word))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
