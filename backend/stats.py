import numpy as np

def normalize_team_name(name):
    if not name: return ""
    name = name.lower().strip()
    # Mapeo de variaciones comunes
    variations = {
        "at.madrid": "atlético",
        "atlético de madrid": "atlético",
        "atletico": "atlético",
        "r.madrid": "real madrid",
        "r. sociedad": "real sociedad",
        "r. oviedo": "oviedo",
        "ath.club": "athletic",
        "athletic club": "athletic",
        "espanyol de barcelona": "espanyol",
        "deportivo de la coruña": "deportivo",
        "racing s.": "racing",
        "r.zaragoza": "zaragoza"
    }
    return variations.get(name, name)

class EloManager:
    def __init__(self, k_factor=32, base_rating=1500):
        self.k_factor = k_factor
        self.base_rating = base_rating
        self.ratings = {} # {team_name: rating}

    def get_rating(self, team):
        team = normalize_team_name(team)
        return self.ratings.get(team, self.base_rating)

    def update_ratings(self, home_team, away_team, result):
        """
        result: 1 (Home Win), 0.5 (Draw), 0 (Away Win)
        """
        home_team = normalize_team_name(home_team)
        away_team = normalize_team_name(away_team)
        r_home = self.get_rating(home_team)
        r_away = self.get_rating(away_team)

        # Expected score
        e_home = 1 / (1 + 10 ** ((r_away - r_home) / 400))
        e_away = 1 - e_home

        # Actual score
        s_home = result
        s_away = 1 - result

        # New ratings
        self.ratings[home_team] = r_home + self.k_factor * (s_home - e_home)
        self.ratings[away_team] = r_away + self.k_factor * (s_away - e_away)

class xGManager:
    def __init__(self, window=10):
        self.window = window
        self.stats = {} # {team_name: {"scored": [], "conceded": []}}

    def update_stats(self, home_team, away_team, home_goals, away_goals):
        home_team = normalize_team_name(home_team)
        away_team = normalize_team_name(away_team)
        if home_team not in self.stats: self.stats[home_team] = {"scored": [], "conceded": []}
        if away_team not in self.stats: self.stats[away_team] = {"scored": [], "conceded": []}

        self.stats[home_team]["scored"].append(home_goals)
        self.stats[home_team]["conceded"].append(away_goals)
        self.stats[away_team]["scored"].append(away_goals)
        self.stats[away_team]["conceded"].append(home_goals)

        # Keep only the window size
        self.stats[home_team]["scored"] = self.stats[home_team]["scored"][-self.window:]
        self.stats[home_team]["conceded"] = self.stats[home_team]["conceded"][-self.window:]
        self.stats[away_team]["scored"] = self.stats[away_team]["scored"][-self.window:]
        self.stats[away_team]["conceded"] = self.stats[away_team]["conceded"][-self.window:]

    def get_projected_xg(self, home_team, away_team):
        home_team = normalize_team_name(home_team)
        away_team = normalize_team_name(away_team)
        # Base xG if no data
        def_val = 1.2
        
        h_scored = np.mean(self.stats.get(home_team, {}).get("scored", [def_val]))
        h_conceded = np.mean(self.stats.get(home_team, {}).get("conceded", [def_val]))
        a_scored = np.mean(self.stats.get(away_team, {}).get("scored", [def_val]))
        a_conceded = np.mean(self.stats.get(away_team, {}).get("conceded", [def_val]))

        # Home team offensive strength vs Away team defensive weakness
        xg_h = (h_scored + a_conceded) / 2
        # Away team offensive strength vs Home team defensive weakness
        xg_a = (a_scored + h_conceded) / 2

        # Adjust for home advantage (approx +15%)
        return xg_h * 1.1, xg_a * 0.9
