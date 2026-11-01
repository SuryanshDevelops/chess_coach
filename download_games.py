
import requests

from datetime import datetime, timedelta, timezone
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


def download_games(
    username,
    time_class,
    game_count=None,
    start_date=None,
    end_date=None,
):
    """
    Download Chess.com games using either:
    1. A recent game count.
    2. A custom date range.
    """

    username = username.strip()

    if not username:
        raise ValueError("Enter a Chess.com username.")

    if isinstance(time_class, str):
        time_classes = {time_class}
    else:
        time_classes = set(time_class)

    if not time_classes:
        raise ValueError("Select at least one game format.")

    # Determine download mode.
    date_mode = start_date is not None or end_date is not None

    if date_mode:

        if start_date is None or end_date is None:
            raise ValueError("Select both a start date and an end date.")

        if start_date > end_date:
            raise ValueError("Start date cannot be after end date.")

        start_timestamp = datetime.combine(
            start_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).timestamp()

        end_timestamp = datetime.combine(
            end_date + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).timestamp()

    else:

        if game_count is None or game_count < 1:
            raise ValueError("Game count must be at least 1.")

    # Get available monthly archives.
    safe_username = quote(username, safe="")

    archives_url = (
        f"https://api.chess.com/pub/player/"
        f"{safe_username}/games/archives"
    )

    archives_data = get_json(archives_url)
    archives = archives_data.get("archives", [])

    selected_archives = []

    if date_mode:

        first_month = (start_date.year, start_date.month)
        last_month = (end_date.year, end_date.month)

        for archive_url in archives:

            parts = archive_url.rstrip("/").split("/")

            year = int(parts[-2])
            month = int(parts[-1])

            archive_month = (year, month)

            if first_month <= archive_month <= last_month:
                selected_archives.append(archive_url)

    else:

        selected_archives = list(reversed(archives))

    if not selected_archives:
        raise ValueError("No Chess.com archives found for this selection.")

    selected_games = []

    # Download only the required monthly archives.
    for archive_url in selected_archives:

        archive_data = get_json(archive_url)

        matching_games = []

        for game in archive_data.get("games", []):

            if game.get("time_class") not in time_classes:
                continue

            if not game.get("pgn"):
                continue

            if date_mode:

                end_time = game.get("end_time", 0)

                if not start_timestamp <= end_time < end_timestamp:
                    continue

            matching_games.append(game)

        matching_games.sort(
            key=lambda game: game.get("end_time", 0),
            reverse=True,
        )

        selected_games.extend(matching_games)

        # Stop early when enough recent games have been collected.
        if not date_mode and len(selected_games) >= game_count:
            break

    selected_games.sort(
        key=lambda game: game.get("end_time", 0),
        reverse=True,
    )

    # Recent mode has a maximum requested count.
    if not date_mode:
        selected_games = selected_games[:game_count]

    if not selected_games:
        raise ValueError(
            "No matching games found for this username, format and period."
        )

    # Save games without creating duplicates.
    new_games = save_games(selected_games, username)

    print(f"New games saved: {new_games}")
    print(f"Games fetched: {len(selected_games)}")

    return DATABASE_PATH, len(selected_games)


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
