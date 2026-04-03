# Quiniela Predictor Pro v1.0 (PRO) 🏆⚽

Sistema avanzado de predicción y optimización para la Quiniela de 15 partidos, impulsado por Inteligencia Artificial y una arquitectura Fullstack robusta.

## 🚀 Características Principales

- **Quiniela 15 Partidos**: Soporte completo para los 14 signos reglamentarios + el Pleno al 15.
- **Multiliga**: Ingesta automática de datos de **Primera División (EA Sports)** y **Segunda División (Hypermotion)**.
- **Motor ML Core**:
  - **PCA (Análisis de Componentes Principales)**: Reducción de dimensionalidad para detectar patrones ocultos.
  - **Logistic Regression**: Predicción probabilística del signo (1X2).
  - **Poisson Goals**: Estimación exacta de goles para el Pleno al 15.
- **Optimizador de Apuestas PRO**: 
  - Cálculo de incertidumbre probabilística.
  - Generación de 3 estrategias (Conservadora R6, Equilibrada R2, Agresiva R1).
  - **Exportación .QUI**: Generación de archivos oficiales para administraciones de lotería.
- **Telegram Bot v2.0**: Interfaz premium con navegación universal, clasificaciones y gestión financiera (ROI/Kelly).

## 🛠️ Stack Tecnológico

- **Backend**: Python 3.10+, FastAPI, SQLAlchemy (PostgreSQL).
- **Frontend**: React, Tailwind CSS, Vite.
- **IA/Data**: Scikit-learn, Pandas, NumPy, BeautifulSoup4 (Scraper).
- **Bot**: Python-telegram-bot.
- **DevOps**: GitHub Actions, Railway (Backend/DB), Vercel (Frontend).

## 📊 Algoritmos y Modelos

El sistema utiliza un pipeline de tres etapas:
1. **Preprocesamiento**: Normalización de estadísticas (Elo, xG, Form) con `StandardScaler`.
2. **Dimensionamiento**: PCA para extraer las características más influyentes del rendimiento.
3. **Clasificación**: Regresión logística multinomial para obtener el `%` de probabilidad de 1, X, 2.
4. **Scoring**: Modelo de Poisson para el pronóstico de goles del partido 15.

## 📥 Uso Rápido (Telegram)

Usa el bot para obtener:
- `/start`: Menú principal premium.
- `📊 Predicción`: Pronóstico con porcentajes y Pleno al 15.
- `🎯 Optimizar Apuesta`: Elige tu riesgo y descarga el archivo `.qui`.
- `🏆 Clasificación`: Tabla real de Primera División (20 equipos).

---
*Desarrollado como solución integral para apostadores de alto rendimiento.*
