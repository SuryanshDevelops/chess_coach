
import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).with_name("chess_coach.db")


def save_games(games, username):
    """Save games to the database without storing duplicates."""

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS games (
                url TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                time_class TEXT NOT NULL,
                end_time INTEGER NOT NULL,
                pgn TEXT NOT NULL
            )
        """)

        new_games = 0

        for game in games:
            game_url = game.get("url")
            pgn_text = game.get("pgn")

            if not game_url or not pgn_text:
                continue

            cursor = connection.execute("""
                INSERT OR IGNORE INTO games
                (url, username, time_class, end_time, pgn)
                VALUES (?, ?, ?, ?, ?)
            """, (
                game_url,
                username.strip(),
                game.get("time_class", "unknown"),
                game.get("end_time", 0),
                pgn_text,
            ))

            new_games += cursor.rowcount

        connection.commit()
        return new_games

    finally:
        connection.close()
