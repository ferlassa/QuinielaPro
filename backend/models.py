from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class Season(Base):
    __tablename__ = 'seasons'
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True) # e.g., "2023-2024"

class Jornada(Base):
    __tablename__ = 'jornadas'
    id = Column(Integer, primary_key=True)
    season_id = Column(Integer, ForeignKey('seasons.id'))
    number = Column(Integer)
    date = Column(DateTime)
    total_recaudacion = Column(Float)
    
    matches = relationship("Match", back_populates="jornada")

class Match(Base):
    __tablename__ = 'matches'
    id = Column(Integer, primary_key=True)
    jornada_id = Column(Integer, ForeignKey('jornadas.id'))
    home_team = Column(String(100))
    away_team = Column(String(100))
    home_goals = Column(Integer)
    away_goals = Column(Integer)
    sign = Column(String(1)) # 1, X, 2
    league_id = Column(Integer) # e.g., 564 (Primera), 384 (Segunda)
    
    # Statistical features
    elo_home = Column(Float)
    elo_away = Column(Float)
    xg_home = Column(Float)
    xg_away = Column(Float)
    
    # Raw features for PCA
    features = Column(JSON) # Store dynamic multivariate data
    
    jornada = relationship("Jornada", back_populates="matches")

class Prediction(Base):
    __tablename__ = 'predictions'
    id = Column(Integer, primary_key=True)
    match_id = Column(Integer, ForeignKey('matches.id'))
    prob_1 = Column(Float)
    prob_x = Column(Float)
    prob_2 = Column(Float)
    edge = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
