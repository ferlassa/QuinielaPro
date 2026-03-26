import os
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Match, Jornada
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from scipy.stats import poisson

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./quiniela.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

class MLEngine:
    def __init__(self, n_components=0.75):
        self.pca = PCA(n_components=n_components)
        self.scaler = StandardScaler()
        self.model_1x2 = LogisticRegression(multi_class='multinomial', max_iter=1000)
        
    def load_training_data(self):
        db = SessionLocal()
        matches = db.query(Match).all()
        
        data = []
        labels = []
        for m in matches:
            # Reconstruct feature vector from JSON or fixed fields
            # For demo, we create a synthetic vector: [goals_h, goals_a, elo_h, elo_a]
            # In production, this would be a large multivariate array
            features = [
                m.home_goals or 0, 
                m.away_goals or 0,
                m.elo_home or 1500,
                m.elo_away or 1500,
                m.xg_home or 1.0,
                m.xg_away or 1.0
            ]
            data.append(features)
            labels.append(m.sign)
            
        db.close()
        return np.array(data), np.array(labels)

    def train(self):
        X, y = self.load_training_data()
        if len(X) < 10:
            print("Datos insuficientes para entrenar PCA/Logit de forma robusta.")
            return
            
        # 1. Scaling
        X_scaled = self.scaler.fit_transform(X)
        
        # 2. PCA
        X_pca = self.pca.fit_transform(X_scaled)
        print(f"PCA completado. Componentes que explican la varianza: {self.pca.n_components_}")
        
        # 3. Logistic Regression
        self.model_1x2.fit(X_pca, y)
        print("Modelo 1X2 entrenado satisfactoriamente.")

    def predict_match(self, home_elo, away_elo, home_xg, away_xg):
        # Prepare input
        features = np.array([[0, 0, home_elo, away_elo, home_xg, away_xg]])
        X_scaled = self.scaler.transform(features)
        X_pca = self.pca.transform(X_scaled)
        
        probs = self.model_1x2.predict_proba(X_pca)[0]
        classes = self.model_1x2.classes_
        prob_dict = dict(zip(classes, probs))
        return {
            "1": float(prob_dict.get("1", 0.33)),
            "X": float(prob_dict.get("X", 0.33)),
            "2": float(prob_dict.get("2", 0.33))
        }

    def predict_poisson_p15(self, home_lambda, away_lambda):
        """
        Calcula la probabilidad exacta de goles para el Pleno al 15.
        Genera matriz de probabilidad de goles (0, 1, 2, M)
        """
        # M se suele representar como 3 o más goles
        goals = [0, 1, 2, 3] # 3 represents 'M'
        
        prob_matrix = np.zeros((4, 4))
        for i, h_g in enumerate(goals):
            for j, a_g in enumerate(goals):
                p_h = poisson.pmf(h_g, home_lambda) if h_g < 3 else (1 - poisson.cdf(2, home_lambda))
                p_a = poisson.pmf(a_g, away_lambda) if a_g < 3 else (1 - poisson.cdf(2, away_lambda))
                prob_matrix[i, j] = p_h * p_a
                
        # Devuelve el resultado más probable (e.g., "2-1")
        idx = np.unravel_index(np.argmax(prob_matrix), prob_matrix.shape)
        res_h = str(idx[0]) if idx[0] < 3 else "M"
        res_a = str(idx[1]) if idx[1] < 3 else "M"
        
        return f"{res_h}-{res_a}", float(np.max(prob_matrix))

if __name__ == "__main__":
    engine = MLEngine()
    # Mock data generation for demo training if DB is empty
    engine.train()
    print("Predicción P15 (Parámetros: H=1.8, A=1.1):", engine.predict_poisson_p15(1.8, 1.1))
