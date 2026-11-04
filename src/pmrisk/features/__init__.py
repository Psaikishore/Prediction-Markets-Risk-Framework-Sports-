"""Pre-game feature construction for NFL games (1999-2026).

Every feature for game g uses only information dated before g's kickoff:
rolling team statistics are shifted by one game, ratings are the pre-game values,
injuries come from the report filed before the game.
"""

# Team code changes: map historical codes to the current franchise code so ratings
# and rolling windows follow the franchise through relocations.
FRANCHISE = {"STL": "LA", "SD": "LAC", "OAK": "LV", "LAR": "LA", "JAC": "JAX", "WSH": "WAS"}


def franchise(code: str) -> str:
    return FRANCHISE.get(code, code)
