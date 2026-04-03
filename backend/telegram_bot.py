import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Configuración básica
# Token y Webhook (Priorizar variables de entorno)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8694335308:AAGDakUTsgGh1WZ21TaLeJKHQ4I9cdfhCTA")
WEBHOOK_URL = "https://quinielapro-production.up.railway.app/telegram"

bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

# --- Helpers de UI ---
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Clasificación y Forma (8J)", callback_data='classification')],
        [InlineKeyboardButton("📊 Predicción 1X2", callback_data='predict')],
        [InlineKeyboardButton("🔄 Sincronizar Resultados", callback_data='sync_db')],
        [InlineKeyboardButton("🛠️ Centro de Diagnóstico", callback_data='health_check')],
        [InlineKeyboardButton("💰 Resumen Financiero", callback_data='financial')],
        [InlineKeyboardButton("🧠 Evolución y Aprendizaje", callback_data='evolution')],
        [InlineKeyboardButton("🌐 Ver App en la Nube", url="https://quiniela-pro-taupe.vercel.app")]
    ])

def get_nav_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Volver al Menú", callback_data='main_menu'),
         InlineKeyboardButton("🌐 Abrir Web App", url="https://quiniela-pro-taupe.vercel.app")]
    ])

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mando principal del bot con teclado premium."""
    keyboard = [
        [InlineKeyboardButton("🏆 Clasificación y Forma (EA Sports)", callback_data='classification')],
        [InlineKeyboardButton("📊 Predicción 1X2", callback_data='predict')],
        [InlineKeyboardButton("🔄 Sincronizar Resultados", callback_data='sync_db')],
        [InlineKeyboardButton("🛠️ Centro de Diagnóstico", callback_data='health_check')],
        [InlineKeyboardButton("💰 Resumen Financiero", callback_data='financial')],
        [InlineKeyboardButton("🎯 Optimizar Apuesta (PRO)", callback_data='optimize')],
        [InlineKeyboardButton("🧠 Evolución y Aprendizaje", callback_data='evolution')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = (
        "⚽ <b>Quiniela Predictor Pro v2.0</b>\n"
        "<i>Datos Reales | IA Auto-Heal | Kelly Criterion</i>\n\n"
        "Selecciona una opción para comenzar:"
    )
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text=text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="HTML")

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
                # 10 de Primera (564) y 5 de Segunda (384) para sumar los 15 de la Quini
                matches_p1 = db.query(Match).filter(Match.jornada_id == first.jornada_id, Match.league_id == 564).limit(10).all()
                matches_p2 = db.query(Match).filter(Match.jornada_id == first.jornada_id, Match.league_id == 384).limit(5).all()
                matches = matches_p1 + matches_p2
                j_num = first.jornada.number
            else:
                matches, j_num = [], "?"
            db.close()
            
            if not matches:
                await query.edit_message_text(text="No quedan jornadas por predecir en la base de datos.", reply_markup=get_nav_keyboard())
                return

            info = [f"📊 <b>Pronóstico Quiniela J{j_num} (15 Partidos)</b>\n"]
            for i, m in enumerate(matches, 1):
                try:
                    p = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                except Exception as e:
                    if "not fitted yet" in str(e): 
                        ml.train()
                        p = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                    else: p = {"1":0.4, "X":0.3, "2":0.3}
                
                sign = max(p, key=p.get)
                p1 = int(p["1"]*100)
                px = int(p["X"]*100)
                p2 = int(p["2"]*100)
                
                label = f"<b>{sign}</b> ({p1}%|{px}%|{p2}%)"
                if i == 15:
                    # Pleno al 15: Predicción de goles exacta
                    try:
                        exact, prob = ml.predict_poisson_p15(m.xg_home or 1.2, m.xg_away or 0.9)
                        label = f"✨ <b>P15: {exact}</b> ({int(prob*100)}%)"
                    except: pass
                
                info.append(f"{i}. {m.home_team[:8]}-{m.away_team[:8]} ➡️ {label}")
            
            await query.edit_message_text(text="\n".join(info), reply_markup=get_nav_keyboard(), parse_mode="HTML")
        except Exception as e:
            import traceback
            open("healer_alerts.log", "a", encoding="utf-8").write(f"PREDICT ERROR: {e}\n{traceback.format_exc()}\n")
            await query.edit_message_text(text=f"🆘 Error Healer: {e}", reply_markup=get_nav_keyboard())

    # --- 2. FINANZAS Y ROI ---
    elif query.data == 'financial':
        try:
            from main import calcular_roi
            r10 = calcular_roi(10)
            roi = round(r10.get("roi_%", 0), 1) if isinstance(r10, dict) else 0
            await query.edit_message_text(text=f"💰 <b>ROI Actual (10J):</b> {roi}%", reply_markup=get_nav_keyboard(), parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error finanzas: {e}", reply_markup=get_nav_keyboard())

    # --- 3. CLASIFICACIÓN REAL ---
    elif query.data == 'classification':
        try:
            from main import SessionLocal
            from models import Match, Jornada
            db = SessionLocal()
            # Filtrar solo Primera División (564) que tengan goles anotados
            matches = db.query(Match).join(Jornada).filter(Match.league_id == 564, Match.home_goals != None).all()
            stats = {}
            for m in matches:
                for t in [m.home_team, m.away_team]:
                    if t not in stats: stats[t] = {"pts":0, "f":[]}
                if m.home_goals > m.away_goals: 
                    stats[m.home_team]["pts"]+=3; stats[m.home_team]["f"].append("✅"); stats[m.away_team]["f"].append("❌")
                elif m.away_goals > m.home_goals: 
                    stats[m.away_team]["pts"]+=3; stats[m.away_team]["f"].append("✅"); stats[m.home_team]["f"].append("❌")
                else: 
                    stats[m.home_team]["pts"]+=1; stats[m.away_team]["pts"]+=1; stats[m.home_team]["f"].append("➖"); stats[m.away_team]["f"].append("➖")
            db.close()
            ranking = sorted(stats.items(), key=lambda x: x[1]["pts"], reverse=True)
            res = [f"🏆 <b>Clasificación Primera División</b>\n"]
            for i, (name, s) in enumerate(ranking[:20], 1):
                res.append(f"{i}. {name[:12]}: {s['pts']} pts [{' '.join(s['f'][-5:])}]")
            await query.edit_message_text(text="\n".join(res), reply_markup=get_nav_keyboard(), parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error tabla: {e}", reply_markup=get_nav_keyboard())

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
            await query.edit_message_text(text="✅ <b>Sincronización OK</b>\nResultados actualizados y motor re-entrenado.", reply_markup=get_nav_keyboard(), parse_mode="HTML")
        except Exception as e:
            import traceback
            open("healer_alerts.log", "a", encoding="utf-8").write(f"SYNC ERROR: {e}\n{traceback.format_exc()}\n")
            await query.edit_message_text(text=f"🆘 Error Sync: {e}", reply_markup=get_nav_keyboard())

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
            await query.edit_message_text(text=msg, reply_markup=get_nav_keyboard(), parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error Salud: {e}", reply_markup=get_nav_keyboard())

    # --- 6. EVOLUCIÓN ---
    elif query.data == 'evolution':
        try:
            from main import ml
            import traceback
            await query.edit_message_text(text="🧠 <i>Optimizando motor...</i>", parse_mode="HTML")
            ml.train()
            await query.edit_message_text(text="✅ <b>Motor IA Optimizado</b>", reply_markup=get_nav_keyboard(), parse_mode="HTML")
        except Exception as e:
            tb = traceback.format_exc()
            await query.edit_message_text(text=f"🆘 <b>Error Crítico:</b> {e}\n<pre>{tb[-500:]}</pre>", reply_markup=get_nav_keyboard(), parse_mode="HTML")

    # --- 7. OPTIMIZADOR DE APUESTAS ---
    elif query.data == 'optimize':
        try:
            from main import ml, SessionLocal
            from models import Match, Jornada
            from optimizer import propose_strategies
            db = SessionLocal()
            matches = db.query(Match).join(Jornada).filter(Match.home_goals == None).order_by(Match.id.asc()).limit(15).all()
            db.close()

            if not matches:
                await query.edit_message_text(text="❌ No hay jornada activa para optimizar.", reply_markup=get_nav_keyboard())
                return

            preds = []
            for m in matches:
                p = ml.predict_match(m.elo_home, m.elo_away, m.xg_home, m.xg_away)
                p['home'] = m.home_team
                p['away'] = m.away_team
                preds.append(p)

            strategies = propose_strategies(preds)
            msg = "🎯 <b>Optimizador Quini PRO</b>\n\nElige una estrategia basada en la jornada actual:\n\n"
            keyboard = []
            for s in strategies:
                msg += f"<b>{s['name']}</b>: {s['desc']}\nCoste: {s['cost']}€\n\n"
                keyboard.append([InlineKeyboardButton(f"Elegir {s['name']}", callback_data=f"strat_{s['id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Volver al Menú", callback_data='main_menu')])
            await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error Optimizador: {e}", reply_markup=get_nav_keyboard())

    elif query.data.startswith('strat_'):
        try:
            from main import ml, SessionLocal
            from models import Match, Jornada
            from optimizer import propose_strategies, export_columns
            strat_id = int(query.data.split('_')[1])
            
            db = SessionLocal()
            matches = db.query(Match).join(Jornada).filter(Match.home_goals == None).order_by(Match.id.asc()).limit(15).all()
            db.close()

            preds = []
            for m in matches:
                p = ml.predict_match(m.elo_home, m.elo_away, m.xg_home, m.xg_away)
                p['home'] = m.home_team
                p['away'] = m.away_team
                preds.append(p)

            strategies = propose_strategies(preds)
            chosen = next(s for s in strategies if s['id'] == strat_id)
            
            # P15 Predicción
            p15_res = ml.predict_poisson_p15(matches[14].xg_home, matches[14].xg_away) if len(matches) > 14 else "1-1"
            
            filename = f"quiniela_{chosen['id']}.qui"
            export_columns(chosen['cols'], p15=p15_res, filepath=filename)
            
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=open(filename, 'rb'),
                caption=f"✅ <b>Apuesta Optimizada Generada</b>\nEstrategia: {chosen['name']}\nColumnas: {len(chosen['cols'])}\nCierre P15: {p15_res}\n\nEnvía este archivo a tu administración local.",
                parse_mode="HTML"
            )
        except Exception as e:
            await query.edit_message_text(text=f"Error Export: {e}", reply_markup=get_nav_keyboard())

    elif query.data == 'main_menu':
        await start_cmd(update, context)

bot_app.add_handler(CommandHandler('start', start_cmd))
bot_app.add_handler(CallbackQueryHandler(button_handler))

async def init_telegram_webhook():
    await bot_app.initialize()
    await bot_app.start()
    success = await bot_app.bot.set_webhook(url=WEBHOOK_URL)
    print(f"Webhook configurado: {success} -> {WEBHOOK_URL}")

async def stop_telegram_webhook():
    await bot_app.stop()
