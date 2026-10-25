
import sqlite3
import io

import chess.pgn
import requests
import streamlit as st

from download_games import download_games
from storage import DATABASE_PATH


st.set_page_config(
    page_title="Chess Coach",
    page_icon="♟",
    layout="wide",
)

FORMATS = {
    "Bullet": ["bullet"],
    "Blitz": ["blitz"],
    "Rapid": ["rapid"],
    "All formats": ["bullet", "blitz", "rapid", "daily"],
}


def load_games(username, formats, game_count):
    """Load the most recent saved games for this user."""

    if not DATABASE_PATH.exists():
        return []

    placeholders = ",".join("?" for _ in formats)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            f"""
            SELECT url, time_class, end_time, pgn
            FROM games
            WHERE lower(username) = lower(?)
              AND time_class IN ({placeholders})
            ORDER BY end_time DESC
            LIMIT ?
            """,
            [username.strip(), *formats, game_count],
        ).fetchall()

        return [dict(row) for row in rows]

    except sqlite3.OperationalError:
        # The database exists but its games table may not yet exist.
        return []

    finally:
        connection.close()


def get_game_stats(game_data, username):
    """Calculate results and ending types for saved games."""

    stats = {
        "played": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,
        "unfinished": 0,
        "checkmate_losses": 0,
        "timeout_losses": 0,
        "resignation_losses": 0,
        "other_losses": 0,
        "stalemate_draws": 0,
    }

    for item in game_data:
        game = chess.pgn.read_game(io.StringIO(item["pgn"]))

        if game is None:
            continue

        headers = game.headers
        white = headers.get("White", "")
        black = headers.get("Black", "")
        result = headers.get("Result", "*")
        termination = headers.get("Termination", "").lower()

        if username.lower() == white.lower():
            user_is_white = True
        elif username.lower() == black.lower():
            user_is_white = False
        else:
            continue

        if result == "*":
            stats["unfinished"] += 1
            continue

        stats["played"] += 1

        if result == "1/2-1/2":
            stats["draws"] += 1

            if "stalemate" in termination:
                stats["stalemate_draws"] += 1

        elif (
            (result == "1-0" and user_is_white)
            or (result == "0-1" and not user_is_white)
        ):
            stats["wins"] += 1

        else:
            stats["losses"] += 1

            if "checkmate" in termination:
                stats["checkmate_losses"] += 1
            elif "time" in termination or "timeout" in termination:
                stats["timeout_losses"] += 1
            elif "resign" in termination:
                stats["resignation_losses"] += 1
            else:
                stats["other_losses"] += 1

    return stats


def show_stats(title, stats):
    """Display summary statistics for one format."""

    st.subheader(title)

    first, second, third, fourth = st.columns(4)

    first.metric("Games played", stats["played"])
    second.metric("Wins", stats["wins"])
    third.metric("Losses", stats["losses"])
    fourth.metric("Draws", stats["draws"])

    completed = stats["played"]

    win_rate = stats["wins"] / completed * 100 if completed else 0
    loss_rate = stats["losses"] / completed * 100 if completed else 0
    draw_rate = stats["draws"] / completed * 100 if completed else 0

    st.write(
        f"Win rate: **{win_rate:.1f}%** · "
        f"Loss rate: **{loss_rate:.1f}%** · "
        f"Draw rate: **{draw_rate:.1f}%**"
    )

    with st.expander("How did your games end?"):
        st.write(f"Checkmate losses: {stats['checkmate_losses']}")
        st.write(f"Timeout losses: {stats['timeout_losses']}")
        st.write(f"Resignation losses: {stats['resignation_losses']}")
        st.write(f"Other or unknown loss endings: {stats['other_losses']}")
        st.write(f"Stalemate draws: {stats['stalemate_draws']}")
        st.write(f"Unfinished games: {stats['unfinished']}")


# Start on the setup page for a new session.
if "page" not in st.session_state:
    st.session_state.page = "setup"


# ---------------- SETUP PAGE ----------------

if st.session_state.page == "setup":

    st.title("♟ Chess Coach")
    st.write("Understand your games. Improve your decisions.")

    if DATABASE_PATH.exists():
        st.success("A saved game database was found.")
    else:
        st.info("No saved database yet. Fetch games to get started.")

    # There is only ONE form on this page.
    with st.form("setup_form"):

        username = st.text_input(
            "Chess.com username",
            placeholder="Enter your username",
        )

        game_format = st.selectbox(
            "Game format",
            list(FORMATS.keys()),
        )

        game_count = st.number_input(
            "Number of games to analyse",
            min_value=1,
            max_value=5000,
            value=100,
            step=10,
        )

        analysis_type = st.radio(
            "What would you like to analyse?",
            ["Full analysis", "A particular game"],
        )

        opponent = ""

        if analysis_type == "A particular game":
            opponent = st.text_input(
                "Opponent's Chess.com username",
                placeholder="Enter opponent username",
            )

        use_saved_games = st.checkbox(
            "Use saved games if available; fetch if none match",
            value=True,
        )

        submitted = st.form_submit_button(
            "Continue to analysis",
            type="primary",
            use_container_width=True,
        )

    # Process the submission ONCE, outside the form.
    if submitted:

        if not username.strip():
            st.error("Enter your Chess.com username.")

        elif (
            analysis_type == "A particular game"
            and not opponent.strip()
        ):
            st.error("Enter the opponent's username.")

        else:
            try:
                selected_formats = FORMATS[game_format]
                count = int(game_count)

                cached_games = []

                if use_saved_games:
                    cached_games = load_games(
                        username,
                        selected_formats,
                        count,
                    )

                if not cached_games:
                    with st.spinner("Fetching games from Chess.com..."):
                        download_games(
                            username,
                            selected_formats,
                            count,
                        )

                # Save the user's choices for the analysis page.
                st.session_state.username = username.strip()
                st.session_state.formats = selected_formats
                st.session_state.game_count = count
                st.session_state.analysis_type = analysis_type
                st.session_state.opponent = opponent.strip()
                st.session_state.page = "analysis"

                st.rerun()

            except ValueError as error:
                st.error(str(error))

            except requests.RequestException as error:
                st.error(f"Chess.com request failed: {error}")


# ---------------- ANALYSIS PAGE ----------------

elif st.session_state.page == "analysis":

    st.title("Your Chess Analysis")

    if st.button("← Back to setup"):
        st.session_state.page = "setup"
        st.rerun()

    username = st.session_state.username
    formats = st.session_state.formats
    game_count = st.session_state.game_count

    games = load_games(username, formats, game_count)

    if not games:
        st.warning(
            "No saved games were found for these settings. "
            "Go back to setup and fetch games again."
        )

    elif st.session_state.analysis_type == "Full analysis":

       st.caption(
    f"Analysing {len(games)} saved games for {username}.")

    for game_format in formats:
            format_games = [
                game
                for game in games
                if game["time_class"] == game_format
            ]

            if format_games:
                stats = get_game_stats(format_games, username)
                show_stats(game_format.title(), stats)

    else:
        opponent = st.session_state.opponent.lower()
        matching_games = []

        for item in games:
            game = chess.pgn.read_game(io.StringIO(item["pgn"]))

            if game is None:
                continue

            white = game.headers.get("White", "")
            black = game.headers.get("Black", "")

            if white.lower() == opponent or black.lower() == opponent:
                matching_games.append((item, game))

        if not matching_games:
            st.warning(
                "No games against this opponent were found among the "
                "loaded games. Try fetching more recent games or "
                "checking the username and format."
            )

        else:
            st.success(
                f"Found {len(matching_games)} matching game(s)."
            )

            selected_index = st.selectbox(
                "Choose a game",
                range(len(matching_games)),
                format_func=lambda i: (
                    f"{matching_games[i][1].headers.get('Date', '?')} | "
                    f"{matching_games[i][1].headers.get('White', '?')} "
                    f"vs "
                    f"{matching_games[i][1].headers.get('Black', '?')}"
                ),
            )

            selected_item, selected_game = matching_games[selected_index]

            st.write(
                f"**Result:** "
                f"{selected_game.headers.get('Result', 'Unknown')}"
            )

            st.write(
                f"**Format:** {selected_item['time_class'].title()}"
            )

            st.write(
                f"**Ending:** "
                f"{selected_game.headers.get('Termination', 'Unknown')}"
            )

            st.info(
                "Game selection works. Detailed move-by-move analysis "
                "will be added next."
            )
