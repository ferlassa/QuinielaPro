import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Configuración básica
# Token y Webhook (Priorizar variables de entorno)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8694335308:AAGDakUTsgGh1WZ21TaLeJKHQ4I9cdfhCTA")
WEBHOOK_URL = "https://quinielapro-production.up.railway.app/telegram"

bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mando principal del bot con teclado premium."""
    keyboard = [
        [InlineKeyboardButton("🏆 Clasificación y Forma (8J)", callback_data='classification')],
        [InlineKeyboardButton("📊 Predicción 1X2", callback_data='predict')],
        [InlineKeyboardButton("🔄 Sincronizar Resultados", callback_data='sync_db')],
        [InlineKeyboardButton("🛠️ Centro de Diagnóstico", callback_data='health_check')],
        [InlineKeyboardButton("💰 Resumen Financiero", callback_data='financial')],
        [InlineKeyboardButton("🧠 Evolución y Aprendizaje", callback_data='evolution')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚽ <b>Quiniela Predictor Pro v2.0</b>\n"
        "<i>Datos Reales | IA Auto-Heal | Kelly Criterion</i>\n\n"
        "Selecciona una opción para comenzar:",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # --- 1. PRONÓSTICO IA ---
    if query.data == 'predict':
        try:
            from main import ml, SessionLocal
            from models import Match
            db = SessionLocal()
            first = db.query(Match).filter(Match.home_goals == None).order_by(Match.id.asc()).first()
            if first:
                matches = db.query(Match).filter(Match.jornada_id == first.jornada_id).all()
                j_num = first.jornada.number
            else:
                matches, j_num = [], "?"
            db.close()
            
            if not matches:
                await query.edit_message_text(text="No quedan jornadas por predecir en la base de datos.")
                return

            info = [f"📊 <b>Pronóstico Jornada {j_num}</b>\n"]
            for i, m in enumerate(matches, 1):
                try:
                    p = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                except Exception as e:
                    if "not fitted yet" in str(e): 
                        ml.train()
                        p = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                    else: p = {"1":0.4, "X":0.3, "2":0.3}
                
                sign = max(p, key=p.get)
                info.append(f"{i}. {m.home_team[:10]}-{m.away_team[:10]} ➡️ <b>{sign}</b>")
            
            await query.edit_message_text(text="\n".join(info), parse_mode="HTML")
        except Exception as e:
            import traceback
            open("healer_alerts.log", "a", encoding="utf-8").write(f"PREDICT ERROR: {e}\n{traceback.format_exc()}\n")
            await query.edit_message_text(text=f"🆘 Error Healer: {e}")

    # --- 2. FINANZAS Y ROI ---
    elif query.data == 'financial':
        try:
            from main import calcular_roi
            r10 = calcular_roi(10)
            roi = round(r10.get("roi_%", 0), 1) if isinstance(r10, dict) else 0
            await query.edit_message_text(text=f"💰 <b>ROI Actual (10J):</b> {roi}%", parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error finanzas: {e}")

    # --- 3. CLASIFICACIÓN REAL ---
    elif query.data == 'classification':
        try:
            from main import SessionLocal
            from models import Match, Jornada
            db = SessionLocal()
            matches = db.query(Match).join(Jornada).filter(Match.home_goals != None).all()
            stats = {}
            for m in matches:
                for t in [m.home_team, m.away_team]:
                    if t not in stats: stats[t] = {"pts":0, "f":[]}
                if m.home_goals > m.away_goals: stats[m.home_team]["pts"]+=3; stats[m.home_team]["f"].append("✅"); stats[m.away_team]["f"].append("❌")
                elif m.away_goals > m.home_goals: stats[m.away_team]["pts"]+=3; stats[m.away_team]["f"].append("✅"); stats[m.home_team]["f"].append("❌")
                else: stats[m.home_team]["pts"]+=1; stats[m.away_team]["pts"]+=1; stats[m.home_team]["f"].append("➖"); stats[m.away_team]["f"].append("➖")
            db.close()
            ranking = sorted(stats.items(), key=lambda x: x[1]["pts"], reverse=True)
            res = [f"🏆 <b>Top 10 Liga Real</b>\n"]
            for i, (name, s) in enumerate(ranking[:10], 1):
                res.append(f"{i}. {name[:12]}: {s['pts']} pts [{''.join(s['f'][-5:])}]")
            await query.edit_message_text(text="\n".join(res), parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error tabla: {e}")

    # --- 4. SINCRONIZACIÓN MANUAL ---
    elif query.data == 'sync_db':
        try:
            from main import SessionLocal, ml
            from scraper import QuinielaScraper
            await query.edit_message_text(text="⏳ <i>Sincronizando Liga...</i>", parse_mode="HTML")
            scraper = QuinielaScraper(api_token="gbyw2CyWtND2QnrfUDtmdHi3i2iC5umjOp52JXF8oNiZwf835sOyBeKikTKu")
            db = SessionLocal()
            await scraper.get_historical_season_real("2026", db)
            db.close()
            # Retraining is part of healing
            ml.train()
            await query.edit_message_text(text="✅ <b>Sincronización OK</b>", parse_mode="HTML")
        except Exception as e:
            import traceback
            open("healer_alerts.log", "a", encoding="utf-8").write(f"SYNC ERROR: {e}\n{traceback.format_exc()}\n")
            await query.edit_message_text(text=f"🆘 Error Sync: {e}")

    # --- 5. CENTRO DE DIAGNÓSTICO (AUTO-HEALER) ---
    elif query.data == 'health_check':
        try:
            from main import SessionLocal, ml
            from models import Match
            db = SessionLocal()
            count = db.query(Match).count()
            db.close()
            msg = f"🩺 <b>Salud del Sistema</b>\nDB: {'✅ OK' if count > 0 else '❌ VACÍA'}\n"
            try: 
                ml.predict_match(1500, 1500, 1.2, 0.9)
                msg += "ML: ✅ OK"
            except Exception:
                ml.train()
                msg += "ML: 🛠️ RE-ENTRENADO"
            await query.edit_message_text(text=msg, parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error Salud: {e}")

    # --- 6. EVOLUCIÓN ---
    elif query.data == 'evolution':
        try:
            from main import ml
            import traceback
            await query.edit_message_text(text="🧠 <i>Optimizando motor...</i>", parse_mode="HTML")
            ml.train()
            await query.edit_message_text(text="✅ <b>Motor IA Optimizado</b>", parse_mode="HTML")
        except Exception as e:
            tb = traceback.format_exc()
            await query.edit_message_text(text=f"🆘 <b>Error Crítico:</b> {e}\n<pre>{tb[-500:]}</pre>", parse_mode="HTML")

bot_app.add_handler(CommandHandler('start', start_cmd))
bot_app.add_handler(CallbackQueryHandler(button_handler))

async def init_telegram_webhook():
    await bot_app.initialize()
    await bot_app.start()
    success = await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook configurado: {success} -> {WEBHOOK_URL}")

async def stop_telegram_webhook():
    await bot_app.stop()
