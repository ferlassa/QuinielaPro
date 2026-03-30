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
    msg = "¡Bienvenido a <b>Quiniela Predictor Pro</b>! 🤖⚽\n\n¿Qué información necesitas hoy?"
    if update.message:
        await update.message.reply_html(msg, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'predict':
        try:
            from main import ml
            probs = ml.predict_match(1500, 1500, 1.2, 0.9)
            p1 = round(probs["1"] * 100, 1)
            px = round(probs["X"] * 100, 1)
            p2 = round(probs["2"] * 100, 1)
            best_sign = max(probs, key=probs.get)
            
            info = f"📊 <b>Predicción Media (Equipos Equilibrados)</b>\n\n1: {p1}%\nX: {px}%\n2: {p2}%\n\n<i>Signo más probable: {best_sign}</i>"
            await query.edit_message_text(text=info, parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error obteniendo datos: {e}")
            
    elif query.data == 'financial':
        try:
            from main import calcular_roi
            from financial import kelly_criterion
            
            r10 = calcular_roi(10)
            r60 = calcular_roi(60)
            roi_10 = round(r10.get("roi_%", 0), 1) if isinstance(r10, dict) else 0
            roi_60 = round(r60.get("roi_%", 0), 1) if isinstance(r60, dict) else 0
            
            # Simulated Kelly for a 51% probability match at 2.0 odds
            kc = kelly_criterion(prob_win=0.51, odds=2.0, bankroll=100.0)
            
            info = f"💰 <b>Estado Financiero Actual</b>\n\n📈 <b>ROI (10 J):</b> {roi_10}%\n📈 <b>ROI (60 J):</b> {roi_60}%\n\n💎 <b>Kelly Apuesta sugerida:</b> {round(kc, 2)}€ (Moderado)"
            await query.edit_message_text(text=info, parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error financiero: {e}")

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
