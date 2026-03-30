import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Token del usuario
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8694335308:AAGDakUTsgGh1WZ21TaLeJKHQ4I9cdfhCTA")
WEBHOOK_URL = "https://quinielapro-production.up.railway.app/telegram"

bot_app = Application.builder().token(TELEGRAM_TOKEN).build()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🌍 Dashboard Principal", callback_data='dashboard')],
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
            from main import ml, SessionLocal
            from models import Match
            
            db = SessionLocal()
            matches = db.query(Match).order_by(Match.id.desc()).limit(14).all()
            db.close()
            matches.reverse()
            
            if not matches:
                await query.edit_message_text(text="No hay partidos en la base de datos.")
                return

            info_lines = ["📊 <b>Pronóstico de la Jornada (14 Partidos)</b>\n"]
            for i, m in enumerate(matches, 1):
                probs = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                p1 = round(probs["1"] * 100, 1)
                px = round(probs["X"] * 100, 1)
                p2 = round(probs["2"] * 100, 1)
                best_sign = max(probs, key=probs.get)
                
                home = m.home_team[:12] if m.home_team else f"Local {i}"
                away = m.away_team[:12] if m.away_team else f"Visitante {i}"
                
                line = f"{i}. {home} - {away} ➡️ <b>{best_sign}</b> ({p1}%-{px}%-{p2}%)"
                info_lines.append(line)
            
            info = "\n".join(info_lines)
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
            kc_dict = kelly_criterion(prob_win=0.51, decimal_odds=2.0, bankroll=100.0)
            kc = kc_dict.get("apuesta_euros", 0)
            
            info = f"💰 <b>Estado Financiero Actual</b>\n\n📈 <b>ROI (10 J):</b> {roi_10}%\n📈 <b>ROI (60 J):</b> {roi_60}%\n\n💎 <b>Kelly Apuesta sugerida:</b> {kc}€ (Moderado)"
            await query.edit_message_text(text=info, parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error financiero: {e}")
            
    elif query.data == 'dashboard':
        try:
            from main import ml, SessionLocal, calcular_roi
            from models import Match
            from financial import kelly_criterion
            
            # 1. Finanzas
            r10 = calcular_roi(10)
            roi_10 = round(r10.get("roi_%", 0), 1) if isinstance(r10, dict) else 0
            kc_dict = kelly_criterion(prob_win=0.51, decimal_odds=2.0, bankroll=100.0)
            kc = kc_dict.get("apuesta_euros", 0)
            
            # 2. Partidos (Preview 3 partidos)
            db = SessionLocal()
            matches = db.query(Match).order_by(Match.id.desc()).limit(14).all()
            db.close()
            matches.reverse()
            
            preview = ""
            for i, m in enumerate(matches[:3], 1):
                probs = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                best_sign = max(probs, key=probs.get)
                home = m.home_team[:8] if m.home_team else f"Loc{i}"
                away = m.away_team[:8] if m.away_team else f"Vis{i}"
                preview += f"• {home} vs {away} ➡️ <b>{best_sign}</b>\n"
                
            info = (
                "🌍 <b>DASHBOARD QUINIELA PRO</b>\n"
                "----------------------------------\n"
                f"📈 <b>ROI (10 J):</b> {roi_10}%\n"
                f"💎 <b>Kelly Apuesta:</b> {kc}€\n"
                "----------------------------------\n"
                "📊 <b>Previa Jornada:</b>\n"
                f"{preview}\n"
                "<i>Pulsa /start para ver todas las opciones.</i>"
            )
            await query.edit_message_text(text=info, parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error cargando dashboard: {e}")

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
