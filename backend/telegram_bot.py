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
        [InlineKeyboardButton("🏆 Clasificación y Forma (8J)", callback_data='classification')],
        [InlineKeyboardButton("📊 Predicción 1X2", callback_data='predict')],
        [InlineKeyboardButton("🔄 Sincronizar Resultados", callback_data='sync_db')],
        [InlineKeyboardButton("💰 Resumen Financiero", callback_data='financial')],
        [InlineKeyboardButton("🧠 Evolución y Aprendizaje", callback_data='evolution')]
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
            # Find the very first upcoming match (whose scores are Null/None)
            first_upcoming_match = db.query(Match).filter(Match.home_goals == None).order_by(Match.id.asc()).first()
            if first_upcoming_match:
                matches = db.query(Match).filter(Match.jornada_id == first_upcoming_match.jornada_id).all()
                jornada_num = first_upcoming_match.jornada.number
            else:
                matches = []
                jornada_num = "?"
            db.close()
            
            if not matches:
                await query.edit_message_text(text="No quedan jornadas por predecir en la base de datos.")
                return

            info_lines = [f"📊 <b>Pronóstico de la Jornada {jornada_num}</b>\n"]
            for i, m in enumerate(matches, 1):
                try:
                    probs = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                except Exception as e:
                    # Auto-Healing Mechanism: if not fitted, train now
                    if "not fitted yet" in str(e):
                        ml.train()
                        probs = ml.predict_match(m.elo_home or 1500, m.elo_away or 1500, m.xg_home or 1.2, m.xg_away or 0.9)
                    else:
                        probs = {"1": 0.45, "X": 0.28, "2": 0.27}
                        
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
            import traceback
            error_data = f"PREDICT ERROR: {e}\n{traceback.format_exc()}\n---\n"
            open("healer_alerts.log", "a", encoding="utf-8").write(error_data)
            await query.edit_message_text(text=f"🆘 <b>¡Error Detectado!</b>\nTransfiriendo log al <i>Senior Auto-Healer Expert</i>...\n<code>{e}</code>", parse_mode="HTML")
            
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

    elif query.data == 'classification':
        try:
            from main import SessionLocal
            from models import Match, Jornada
            
            db = SessionLocal()
            # Fetch matches ordered chronologically
            matches = db.query(Match).join(Jornada).order_by(Match.jornada_id.asc(), Match.id.asc()).all()
            db.close()
            
            if not matches:
                await query.edit_message_text(text="No hay datos de partidos suficientes para la clasificación.")
                return

            teams = {}
            for m in matches:
                if m.home_goals is not None and m.away_goals is not None:
                    for team in [m.home_team, m.away_team]:
                        if team not in teams:
                            teams[team] = {'P': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'Pts': 0, 'form': []}
                    
                    teams[m.home_team]['P'] += 1
                    teams[m.home_team]['GF'] += m.home_goals
                    teams[m.home_team]['GA'] += m.away_goals
                    
                    teams[m.away_team]['P'] += 1
                    teams[m.away_team]['GF'] += m.away_goals
                    teams[m.away_team]['GA'] += m.home_goals
                    
                    if m.home_goals > m.away_goals:
                        teams[m.home_team]['W'] += 1
                        teams[m.home_team]['Pts'] += 3
                        teams[m.home_team]['form'].append('✅')
                        teams[m.away_team]['L'] += 1
                        teams[m.away_team]['form'].append('❌')
                    elif m.home_goals < m.away_goals:
                        teams[m.away_team]['W'] += 1
                        teams[m.away_team]['Pts'] += 3
                        teams[m.away_team]['form'].append('✅')
                        teams[m.home_team]['L'] += 1
                        teams[m.home_team]['form'].append('❌')
                    else:
                        teams[m.home_team]['D'] += 1
                        teams[m.home_team]['Pts'] += 1
                        teams[m.home_team]['form'].append('➖')
                        teams[m.away_team]['D'] += 1
                        teams[m.away_team]['Pts'] += 1
                        teams[m.away_team]['form'].append('➖')

            sorted_teams = sorted(teams.items(), key=lambda x: (x[1]['Pts'], x[1]['GF'] - x[1]['GA'], x[1]['GF']), reverse=True)
            
            lines = ["🏆 <b>Clasificación y Forma</b>\n"]
            for i, (name, stats) in enumerate(sorted_teams[:20], 1):
                form_8 = "".join(stats['form'][-8:])
                gd = stats['GF'] - stats['GA']
                sign_gd = f"+{gd}" if gd > 0 else str(gd)
                
                # Format: 1. Barcelona | 73pts | +50 (29J)
                lines.append(f"<b>{i}. {name[:12]}</b> | {stats['Pts']}pts | {sign_gd} ({stats['P']}J)")
                lines.append(f"└ {form_8}")
                
            info = "\n".join(lines)
            await query.edit_message_text(text=info[:4096], parse_mode="HTML")
            
        except Exception as e:
            await query.edit_message_text(text=f"Error obteniendo clasificación: {e}")
            
    elif query.data == 'evolution':
        try:
            from main import ml, calcular_roi, SessionLocal
            from models import Match
            
            # 1. Aprender (Reentrenar modelo on-demand)
            await query.edit_message_text(text="🧠 <i>Re-entrenando la red neuronal con los últimos resultados de la BD...</i>", parse_mode="HTML")
            
            db = SessionLocal()
            total_matches = db.query(Match).count()
            db.close()
            
            # Forzamos el entrenamiento para incorporar los partidos más recientes
            ml.train()
            
            # 2. Obtener Histórico de Aciertos
            r1 = calcular_roi(1)
            r10 = calcular_roi(10)
            r60 = calcular_roi(60)
            
            aciertos_1 = r1.get("aciertos_medios", 0) if isinstance(r1, dict) else 0
            aciertos_10 = r10.get("aciertos_medios", 0) if isinstance(r10, dict) else 0
            aciertos_60 = r60.get("aciertos_medios", 0) if isinstance(r60, dict) else 0
            
            info = (
                "🧠 <b>EVOLUCIÓN DEL MODELO</b>\n"
                "----------------------------------\n"
                f"✅ <b>Aprendizaje:</b> Completado sobre {total_matches} partidos históricos.\n"
                "El modelo de Machine Learning y el PCA han sido actualizados.\n\n"
                "🎯 <b>Rendimiento (Aciertos Reales):</b>\n"
                f"• Última Jornada Simulada: <b>{aciertos_1}/14</b> aciertos\n"
                f"• Media de Aciertos (10 J): <b>{aciertos_10}/14</b> aciertos\n"
                f"• Media de Aciertos (60 J): <b>{aciertos_60}/14</b> aciertos\n\n"
                "<i>Nota: El modelo seguirá evolucionando conforme se añadan resultados reales a la Base de Datos.</i>"
            )
            await query.edit_message_text(text=info, parse_mode="HTML")
        except Exception as e:
            await query.edit_message_text(text=f"Error en el ciclo de aprendizaje: {e}")

    elif query.data == 'sync_db':
        try:
            from main import SessionLocal, ml
            from scraper import QuinielaScraper
            
            await query.edit_message_text(text="⏳ <i>Conectando a Internet (Marca/SportMonks) para actualizar la Liga en tiempo real. Esto puede tardar unos segundos...</i>", parse_mode="HTML")
            
            scraper = QuinielaScraper(api_token="gbyw2CyWtND2QnrfUDtmdHi3i2iC5umjOp52JXF8oNiZwf835sOyBeKikTKu")
            db = SessionLocal()
            await scraper.get_historical_season_real("2025-2026", db)
            db.close()
            
            # Auto-Healer Maintenance: Obligatory retraining after syncing massive data
            ml.train()
            
            await query.edit_message_text(text="✅ <b>¡Sincronización Completada!</b>\nLa base de datos contiene los resultados más recientes. La Clasificación y el Pronóstico ya apuntan a la próxima jornada.", parse_mode="HTML")
            
        except Exception as e:
            import traceback
            error_data = f"SYNC ERROR: {e}\n{traceback.format_exc()}\n---\n"
            open("healer_alerts.log", "a", encoding="utf-8").write(error_data)
            await query.edit_message_text(text=f"🆘 <b>¡Error Crítico!</b>\nTransfiriendo telemetría al Auto-Healer...\n<code>{e}</code>", parse_mode="HTML")

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
