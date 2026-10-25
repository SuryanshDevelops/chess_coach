import requests
from urllib.parse import quote
from storage import save_games, DATABASE_PATH


def get_json(url):
    """Download JSON data from Chess.com's public API."""

    response = requests.get(
        url,
        headers={"User-Agent": "ChessCoach/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def download_games(username, time_class, game_count):
    """Download recent games and return their file path and count."""

    username = username.strip()

    if not username:
        raise ValueError("Enter a Chess.com username.")

    if game_count < 1:
        raise ValueError("Game count must be at least 1.")

    # Allow one format or a list of formats.
    if isinstance(time_class, str):
        time_classes = {time_class}
    else:
        time_classes = set(time_class)

    safe_username = quote(username, safe="")
    archives_url = (
        f"https://api.chess.com/pub/player/"
        f"{safe_username}/games/archives"
    )

    archives_data = get_json(archives_url)
    archives = archives_data.get("archives", [])

    selected_games = []

    # Examine the newest monthly archives first.
    for archive_url in reversed(archives):
        archive_data = get_json(archive_url)

        matching_games = [
            game
            for game in archive_data.get("games", [])
            if game.get("time_class") in time_classes
            and game.get("pgn")
        ]

        matching_games.sort(
            key=lambda game: game.get("end_time", 0),
            reverse=True,
        )

        selected_games.extend(matching_games)

        if len(selected_games) >= game_count:
            break

    # Keep only the newest requested games.
    selected_games.sort(
        key=lambda game: game.get("end_time", 0),
        reverse=True,
    )
    selected_games = selected_games[:game_count]

    if not selected_games:
        raise ValueError(
            "No matching games found for that username and format."
        )

       # Save games to the database without overwriting older games.
    new_games = save_games(selected_games, username)

    print(f"New games saved: {new_games}")
    print(f"Games fetched: {len(selected_games)}")

    return DATABASE_PATH, len(selected_games)     

    try:
        game_count = int(input("How many recent games? "))

        output_path, count = download_games(
            username,
            formats[choice],
            game_count,
        )

        print(f"Downloaded {count} games.")
        print(f"Saved to: {output_path}")

    except ValueError as error:
        print(f"Could not download games: {error}")

    except requests.RequestException as error:
        print(f"Chess.com request failed: {error}")
def main():
    """Allow the downloader to run independently from the terminal."""

    username = input("Chess.com username: ").strip()

    formats = {
        "1": "bullet",
        "2": "blitz",
        "3": "rapid",
        "4": "daily",
    }

    print("\nChoose a game format:")
    print("1. Bullet")
    print("2. Blitz")
    print("3. Rapid")
    print("4. Daily")

    choice = input("Enter 1, 2, 3, or 4: ").strip()

    if choice not in formats:
        print("Invalid format choice.")
        return

    try:
        game_count = int(input("How many recent games? "))

        output_path, count = download_games(
            username,
            formats[choice],
            game_count,
        )

        print(f"Fetched {count} games.")
        print(f"Database: {output_path}")

    except ValueError as error:
        print(f"Could not download games: {error}")

    except requests.RequestException as error:
        print(f"Chess.com request failed: {error}")


if __name__ == "__main__":
    main()

