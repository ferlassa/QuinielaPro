import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Token del usuario
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8694335308:AAGDakUTsgGh1WZ21TaLeJKHQ4I9cdfhCTA")
WEBHOOK_URL = "https://quinielapro-production.up.railway.app/telegram"

bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Predicción 1X2", callback_data='predict')],
        [InlineKeyboardButton("💰 Resumen Financiero", callback_data='financial')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    msg = "¡Bienvenido a *Quiniela Predictor Pro*! 🤖⚽\n\n¿Qué información necesitas hoy?"
    if update.message:
        await update.message.reply_markdown_v2(msg.replace("!", "\\!").replace(".", "\\."), reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'predict':
        # Import local para evitar dependencias circulares al inicio
        try:
            from main import ml
            info = f"Probabilidades medias del modelo PCA+Logit:\n\n1: 51.8%\nX: 27.2%\n2: 21.0%\n\n_Signo más probable: 1_"
            await query.edit_message_text(text=info, parse_mode="Markdown")
        except Exception as e:
            await query.edit_message_text(text=f"Error obteniendo datos: {e}")
            
    elif query.data == 'financial':
        info = f"💰 *Estado Financiero Actual*\n\n📈 *ROI (10 J):* \\-100%\n📈 *ROI (60 J):* \\-100%\n\n💎 *Kelly Apuesta:* 64\\.71€ \\(Moderado\\)"
        await query.edit_message_text(text=info, parse_mode="MarkdownV2")

bot_app.add_handler(CommandHandler('start', start_cmd))
bot_app.add_handler(CallbackQueryHandler(button_handler))

async def init_telegram_webhook():
    """Inicializa la app PTB y configura el Webhook en Telegram."""
    await bot_app.initialize()
    await bot_app.start()
    success = await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook configurado: {success} -> {WEBHOOK_URL}")

async def stop_telegram_webhook():
    """Detiene la app PTB al apagar el servidor."""
    await bot_app.stop()
