import chess.svg
import sqlite3
import io
from datetime import date
import chess.pgn
import requests
import streamlit as st

from download_games import download_games
from storage import DATABASE_PATH


def load_default_username():
    """Load the saved default Chess.com username."""

    if not DATABASE_PATH.exists():
        return ""

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = ?",
            ("default_username",),
        ).fetchone()

        return row[0] if row else ""

    except sqlite3.OperationalError:
        return ""

    finally:
        connection.close()


def save_default_username(username):
    """Permanently save the default Chess.com username."""

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        connection.execute(
            """
            INSERT OR REPLACE INTO settings (key, value)
            VALUES (?, ?)
            """,
            ("default_username", username.strip()),
        )

        connection.commit()

    finally:
        connection.close()


st.set_page_config(
    page_title="Chess Coach",
    page_icon="♟",
    layout="wide",)

# ---------------- CUSTOM DESIGN ----------------

st.markdown("""
<style>

/* Main application background */
.stApp {
    background-color: #F5F7F4;
    color: #202820;
}

/* Main content spacing */
.block-container {
    max-width: 1250px;
    padding-top: 2.5rem;
    padding-bottom: 3rem;
}

/* Main headings */
h1 {
    color: #202820 !important;
    font-weight: 700 !important;
    letter-spacing: -1.2px;
}

h2, h3 {
    color: #29382C !important;
    font-weight: 650 !important;
    letter-spacing: -0.4px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #FFFFFF;
    border-right: 1px solid #E7EBE5;
}

/* Buttons */
.stButton > button {
    border-radius: 9px;
    border: 1px solid #DCE4DA;
    background-color: #FFFFFF;
    color: #29382C;
    font-weight: 600;
    padding: 0.55rem 1rem;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    border-color: #527A5A;
    color: #527A5A;
    background-color: #F3F7F2;
}

/* Primary buttons */
.stButton > button[kind="primary"],
.stFormSubmitButton > button {
    background-color: #527A5A;
    color: white;
    border: 1px solid #527A5A;
}

.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button:hover {
    background-color: #416649;
    color: white;
}

/* Input fields */
.stTextInput input,
.stNumberInput input,
.stSelectbox div[data-baseweb="select"] {
    border-radius: 8px;
}

/* Metric cards */
[data-testid="stMetric"] {
    background-color: #FFFFFF;
    border: 1px solid #E7EBE5;
    padding: 18px;
    border-radius: 12px;
}

/* Expanders */
[data-testid="stExpander"] {
    background-color: #FFFFFF;
    border: 1px solid #E7EBE5;
    border-radius: 10px;
}

/* Horizontal separators */
hr {
    border-color: #E7EBE5;
}

/* Captions */
.stCaption {
    color: #788278;
}

/* Remove unnecessary top decoration */
[data-testid="stDecoration"] {
    display: none;
}

</style>
""", unsafe_allow_html=True)


FORMATS = {
    "Bullet": ["bullet"],
    "Blitz": ["blitz"],
    "Rapid": ["rapid"],
    "All formats": ["bullet", "blitz", "rapid", "daily"],
}



from datetime import datetime, timedelta, timezone


def load_games(
    username,
    formats,
    game_count=5000,
    start_date=None,
    end_date=None,
):
    """Load saved games with optional date filters."""

    if not username.strip() or not formats:
        return []

    if not DATABASE_PATH.exists():
        return []

    placeholders = ",".join("?" for _ in formats)

    query = f"""
        SELECT url, time_class, end_time, pgn
        FROM games
        WHERE lower(username) = lower(?)
          AND time_class IN ({placeholders})
    """

    parameters = [username.strip(), *formats]

    if start_date is not None:

        start_timestamp = datetime.combine(
            start_date,
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).timestamp()

        query += " AND end_time >= ?"
        parameters.append(start_timestamp)

    if end_date is not None:

        end_timestamp = datetime.combine(
            end_date + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        ).timestamp()

        query += " AND end_time < ?"
        parameters.append(end_timestamp)

    query += " ORDER BY end_time DESC LIMIT ?"
    parameters.append(game_count)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    try:

        rows = connection.execute(
            query,
            parameters,
        ).fetchall()

        return [dict(row) for row in rows]

    except sqlite3.OperationalError:
        return []

    finally:
        connection.close()




def get_game_stats(game_data, username):
    """Calculate results and classify chess game endings."""

    stats = {
        "played": 0,
        "wins": 0,
        "losses": 0,
        "draws": 0,

        # Loss categories
        "checkmate_losses": 0,
        "timeout_losses": 0,
        "resignation_losses": 0,

        # Draw categories
        "stalemate_draws": 0,
        "repetition_draws": 0,
        "fifty_move_draws": 0,
        "insufficient_material_draws": 0,
        "agreement_draws": 0,

        "unfinished": 0,
    }

    for item in game_data:

        game = chess.pgn.read_game(
            io.StringIO(item["pgn"])
        )

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

        board = game.end().board()

        # ---------------- WINS ----------------

        if (
            (result == "1-0" and user_is_white)
            or (result == "0-1" and not user_is_white)
        ):

            stats["wins"] += 1

        # ---------------- LOSSES ----------------

        elif (
            (result == "0-1" and user_is_white)
            or (result == "1-0" and not user_is_white)
        ):

            stats["losses"] += 1

            if board.is_checkmate():
                stats["checkmate_losses"] += 1

            elif "time" in termination or "timeout" in termination:
                stats["timeout_losses"] += 1

            elif "resign" in termination:
                stats["resignation_losses"] += 1

            

        # ---------------- DRAWS ----------------

        elif result == "1/2-1/2":

            stats["draws"] += 1

            # Prefer explicit termination information when available.
            if "stalemate" in termination:
                stats["stalemate_draws"] += 1

            elif "repetition" in termination:
                stats["repetition_draws"] += 1

            elif "50" in termination or "fifty" in termination:
                stats["fifty_move_draws"] += 1

            elif "insufficient" in termination:
                stats["insufficient_material_draws"] += 1

            elif "agreement" in termination:
                stats["agreement_draws"] += 1

            # Otherwise inspect the final board and move history.
            elif board.is_stalemate():
                stats["stalemate_draws"] += 1

            elif board.is_repetition(3):
                stats["repetition_draws"] += 1

            elif board.is_fifty_moves():
                stats["fifty_move_draws"] += 1

            elif board.is_insufficient_material():
                stats["insufficient_material_draws"] += 1

            

    return stats


def show_stats(title, stats):
    """Display summary statistics and game-ending breakdown."""

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

        st.markdown("**Loss breakdown**")

        st.write(f"Checkmate: {stats['checkmate_losses']}")
        st.write(f"Timeout: {stats['timeout_losses']}")
        st.write(f"Resignation: {stats['resignation_losses']}")

        st.divider()

        st.markdown("**Draw breakdown**")

        st.write(f"Stalemate: {stats['stalemate_draws']}")
        st.write(f"Threefold repetition: {stats['repetition_draws']}")
        st.write(f"50-move rule: {stats['fifty_move_draws']}")
        st.write(
            f"Insufficient material: "
            f"{stats['insufficient_material_draws']}"
        )
        st.write(f"Draw by agreement: {stats['agreement_draws']}")


# ---------------- SIDEBAR NAVIGATION ----------------

if "page" not in st.session_state:
    st.session_state.page = "setup"

if "menu" not in st.session_state:
    st.session_state.menu = "Dashboard"

if "username" not in st.session_state:
    st.session_state.username = ""
if "default_username" not in st.session_state:
    st.session_state.default_username = load_default_username()

if "formats" not in st.session_state:
    st.session_state.formats = []

if "game_count" not in st.session_state:
    st.session_state.game_count = 100

if "analysis_type" not in st.session_state:
    st.session_state.analysis_type = "Full analysis"

if "opponent" not in st.session_state:
    st.session_state.opponent = ""

with st.sidebar:

    st.markdown(
        "<h2 style='margin-bottom:0;'>♟ Chess Coach</h2>",
        unsafe_allow_html=True,
    )

    st.caption("Your personal chess workspace")
    st.divider()

    st.markdown("### Workspace")

    pages = ["Dashboard", "My Games", "Statistics", "Settings"]

    for page_name in pages:

        is_active = st.session_state.menu == page_name

        if st.button(
            page_name,
            key=f"nav_{page_name}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):

            st.session_state.menu = page_name

            if page_name == "Dashboard":
                st.session_state.page = "setup"

            elif page_name == "My Games":
                st.session_state.page = "my_games"

            elif page_name == "Statistics":
                st.session_state.page = "statistics"

            elif page_name == "Settings":
                st.session_state.page = "settings"

            st.rerun()


    st.divider()

    st.caption("CHESS COACH")
    st.caption("Personal game analytics")




# ---------------- DASHBOARD: DOWNLOAD GAMES ----------------

if st.session_state.page == "setup":

    st.markdown(
        "<h1 style='font-size: 38px;'>Game Downloader</h1>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<p style='color: #788278; font-size: 16px;'>"
        "Download and save your Chess.com games."
        "</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Choose how games should be downloaded.
    download_mode = st.selectbox(
        "Download method",
        ["Recent games", "Date range"],
        key="download_mode",
    )

    with st.form("download_form"):

        username = st.text_input(
            "Chess.com username",
            value=st.session_state.default_username,
            placeholder="Enter Chess.com username",
        )

        game_format = st.selectbox(
            "Game format",
            list(FORMATS.keys()),
        )

        # Recent games mode.
        if download_mode == "Recent games":

            game_count = st.number_input(
                "Number of recent games to fetch",
                min_value=1,
                max_value=5000,
                value=100,
                step=10,
            )

        # Historical date-range mode.
        else:

            st.caption(
                "Select the period for which you want to download games. "
                "Dates are interpreted in UTC."
            )

            col1, col2 = st.columns(2)

            with col1:
                start_date = st.date_input(
                    "Start date",
                    value=date(2025, 1, 1),
                    max_value=date.today(),
                )

            with col2:
                end_date = st.date_input(
                    "End date",
                    value=date.today(),
                    max_value=date.today(),
                )

        submitted = st.form_submit_button(
            "Download games",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        if not username.strip():

            st.error("Enter a Chess.com username.")

        else:

            try:

                selected_formats = FORMATS[game_format]

                with st.spinner("Fetching games from Chess.com..."):

                    if download_mode == "Recent games":

                        count = int(game_count)

                        database_path, fetched_count = download_games(
                            username.strip(),
                            selected_formats,
                            count,
                        )

                    else:

                        if start_date > end_date:
                            st.error(
                                "Start date cannot be after end date."
                            )
                            st.stop()

                        database_path, fetched_count = download_games(
                            username.strip(),
                            selected_formats,
                            start_date=start_date,
                            end_date=end_date,
                        )

                st.session_state.username = username.strip()
                st.session_state.formats = selected_formats

                if download_mode == "Recent games":
                    st.session_state.game_count = count

                st.success(
                    f"Successfully fetched {fetched_count} games "
                    f"for {username.strip()}."
                )

                st.caption(
                    "Your games have been saved in the local database."
                )

            except ValueError as error:

                st.error(str(error))

            except requests.RequestException as error:

                st.error(f"Chess.com request failed: {error}")


# ---------------- SETTINGS PAGE ----------------

elif st.session_state.page == "settings":

    st.title("Settings")
    st.caption("Customize your Chess Coach experience.")

    st.divider()

    st.subheader("Appearance")

    board_theme = st.selectbox(
        "Chessboard colour",
        [
            "Classic Green",
            "Blue",
            "Brown",
            "Purple",
        ],
    )

    piece_style = st.selectbox(
        "Chess piece style",
        [
            "Standard",
            "Classic",
        ],
    )

    st.divider()

    st.subheader("Account")

    settings_username = st.text_input(
        "Default Chess.com username",
        value=st.session_state.default_username,
        placeholder="Enter your Chess.com username",
    )

    if st.button("Save settings", type="primary"):

        if not settings_username.strip():

            st.error("Please enter a Chess.com username.")

        else:

            save_default_username(settings_username)

            st.session_state.default_username = settings_username.strip()

            st.session_state.board_theme = board_theme
            st.session_state.piece_style = piece_style

            st.success("Settings saved successfully.")




# ---------------- MY GAMES PAGE ----------------

elif st.session_state.page == "my_games":

    st.title("My Games")

    # Initialize page state.
    if "my_games_show_results" not in st.session_state:
        st.session_state.my_games_show_results = False
    if "selected_game" not in st.session_state:
        st.session_state.selected_game = None
    # ---------------- FILTER SCREEN ----------------

    if not st.session_state.my_games_show_results:

        st.caption("Choose your filters to browse saved games.")

        st.divider()

        with st.form("my_games_filter_form"):

            username = st.text_input(
                "Chess.com username",
                value=(
                    st.session_state.username
                    or st.session_state.default_username
                ),
                placeholder="Enter any Chess.com username",
            )

            st.subheader("Filters")

            col1, col2 = st.columns(2)

            with col1:
                selected_format = st.selectbox(
                    "Game format",
                    ["All", "Bullet", "Blitz", "Rapid", "Daily"],
                )

            with col2:
                selected_result = st.selectbox(
                    "Result",
                    ["All", "Win", "Loss", "Draw", "Unfinished"],
                )

            opponent_search = st.text_input(
                "Opponent",
                placeholder="Search opponent username...",
            )

            use_date_filter = st.checkbox("Filter by date")

            start_date = None
            end_date = None

            if use_date_filter:

                col1, col2 = st.columns(2)

                with col1:
                    start_date = st.date_input(
                        "Start date",
                        value=date(2025, 1, 1),
                        max_value=date.today(),
                    )

                with col2:
                    end_date = st.date_input(
                        "End date",
                        value=date.today(),
                        max_value=date.today(),
                    )

            game_count = st.number_input(
                "Maximum games to display",
                min_value=1,
                max_value=5000,
                value=100,
                step=10,
            )

            submitted = st.form_submit_button(
                "Show Games",
                type="primary",
                use_container_width=True,
            )

        if submitted:

            if not username.strip():

                st.error("Enter a Chess.com username.")

            elif (
                use_date_filter
                and start_date > end_date
            ):

                st.error("Start date cannot be after end date.")

            else:

                # Save selected filters.
                st.session_state.my_games_filters = {
                    "username": username.strip(),
                    "format": selected_format,
                    "result": selected_result,
                    "opponent": opponent_search.strip(),
                    "start_date": start_date if use_date_filter else None,
                    "end_date": end_date if use_date_filter else None,
                    "game_count": int(game_count),
                }

                st.session_state.my_games_show_results = True
                st.rerun()

    # ---------------- RESULTS SCREEN ----------------

    else:

        filters = st.session_state.my_games_filters

        username = filters["username"]

        st.caption(f"Saved games for {username}")

        if st.button("← Back to Filters"):
             st.session_state.my_games_show_results = False
             st.session_state.selected_game = None
             st.rerun()
        st.divider()

        # Determine formats.
        if filters["format"] == "All":
            formats = ["bullet", "blitz", "rapid", "daily"]
        else:
            formats = [filters["format"].lower()]

        # Load saved games.
        games = load_games(
            username,
            formats,
            5000,
            start_date=filters["start_date"],
            end_date=filters["end_date"],
        )

        if not games:

            st.warning(
                "No saved games found for this selection. "
                "Download games from Dashboard first."
            )

        else:

            filtered_games = []

            # Process PGN files.
            for item in games:

                game = chess.pgn.read_game(
                    io.StringIO(item["pgn"])
                )

                if game is None:
                    continue

                white = game.headers.get("White", "Unknown")
                black = game.headers.get("Black", "Unknown")
                result = game.headers.get("Result", "*")

                if white.lower() == username.lower():

                    opponent = black

                    if result == "1-0":
                        outcome = "Win"
                    elif result == "0-1":
                        outcome = "Loss"
                    elif result == "1/2-1/2":
                        outcome = "Draw"
                    else:
                        outcome = "Unfinished"

                elif black.lower() == username.lower():

                    opponent = white

                    if result == "0-1":
                        outcome = "Win"
                    elif result == "1-0":
                        outcome = "Loss"
                    elif result == "1/2-1/2":
                        outcome = "Draw"
                    else:
                        outcome = "Unfinished"

                else:
                    continue

                # Apply result filter.
                if (
                    filters["result"] != "All"
                    and outcome != filters["result"]
                ):
                    continue

                # Apply opponent filter.
                if (
                    filters["opponent"].lower()
                    not in opponent.lower()
                ):
                    continue

                filtered_games.append({
                    "opponent": opponent,
                    "outcome": outcome,
                    "format": item["time_class"].title(),
                    "date": game.headers.get("Date", "Unknown"),
                    "url": item["url"],
                    "pgn": item["pgn"],
                    "white": white,
                    "black": black,
                    "result": result,})

            # ---------------- DISPLAY RESULTS ----------------

            displayed_games = filtered_games[:filters["game_count"]]
           
            
            # ---------------- INDIVIDUAL GAME REVIEW ----------------

            if st.session_state.selected_game is not None:

                selected_game = st.session_state.selected_game

                if st.button("← Back to Games"):
                    st.session_state.selected_game = None
                    st.rerun()

                st.divider()
                st.title("Game Review")

                st.subheader(
                    f"{selected_game['white']} vs {selected_game['black']}"
                )

                col1, col2, col3 = st.columns(3)

                col1.metric("Result", selected_game["result"])
                col2.metric("Format", selected_game["format"])
                col3.metric("Date", selected_game["date"])

                st.divider()

                # Parse the selected game's PGN.
                review_game = chess.pgn.read_game(
                    io.StringIO(selected_game["pgn"])
                )

                if review_game is not None:

                    st.subheader("Game Board")

                    # Reset navigation when a different game is selected.
                    if st.session_state.get("review_game_url") != selected_game["url"]:
                        st.session_state.review_game_url = selected_game["url"]
                        st.session_state.review_move_index = 0

                    # Reconstruct every position in the game.
                    board = review_game.board()
                    positions = [board.copy()]
                    move_records = []

                    for move in review_game.mainline_moves():

                        move_number = board.fullmove_number
                        san_move = board.san(move)

                        if board.turn == chess.WHITE:
                            move_label = f"{move_number}. {san_move}"
                        else:
                            move_label = f"{move_number}... {san_move}"

                        board.push(move)

                        move_records.append({
                            "label": move_label,
                            "move": move,
                        })

                        positions.append(board.copy())

                    # Keep the selected index within the game's move range.
                    move_index = st.session_state.review_move_index
                    move_index = min(move_index, len(move_records))
                    move_index = max(move_index, 0)

                    st.session_state.review_move_index = move_index

                    # Get the position currently being viewed.
                    current_board = positions[move_index]

                    last_move = (
                        move_records[move_index - 1]["move"]
                        if move_index > 0
                        else None
                    )

                    # Display the chessboard.
                    board_svg = chess.svg.board(
                        board=current_board,
                        lastmove=last_move,
                        size=650,
                        coordinates=True,
                    )

                    st.html(
                         f"""
                         <div style="
                        width: 100%;
                        max-width: 680px;
                        margin: auto;
                         "> {board_svg} </div>""")
                    # Show the current position's move.
                    if move_index == 0:
                        st.info("Starting Position")
                    else:
                        st.markdown(
                            f"**Current move:** "
                            f"{move_records[move_index - 1]['label']}"
                        )

                    st.caption(
                        f"Position {move_index} of {len(move_records)} moves"
                    )

                    # Navigation controls.
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        if st.button(
                            "⏮ First",
                            disabled=move_index == 0,
                            use_container_width=True,
                        ):
                            st.session_state.review_move_index = 0
                            st.rerun()

                    with col2:
                        if st.button(
                            "← Previous",
                            disabled=move_index == 0,
                            use_container_width=True,
                        ):
                            st.session_state.review_move_index -= 1
                            st.rerun()

                    with col3:
                        if st.button(
                            "Next →",
                            disabled=move_index == len(move_records),
                            use_container_width=True,
                        ):
                            st.session_state.review_move_index += 1
                            st.rerun()

                    with col4:
                        if st.button(
                            "Last ⏭",
                            disabled=move_index == len(move_records),
                            use_container_width=True,
                        ):
                            st.session_state.review_move_index = len(move_records)
                            st.rerun()

                else:
                    st.error("Could not read this game's PGN.")

            # ---------------- DISPLAY GAME RESULTS ----------------

            else:

                st.subheader("Game Results")

                st.caption(
                    f"{len(filtered_games)} matching games found. "
                    f"Showing {len(displayed_games)}."
                )

                if not displayed_games:

                    st.info("No games match your selected filters.")

                else:

                    for index, game in enumerate(displayed_games):

                        game_date = game["date"].replace(".", "-")

                        with st.container(border=True):

                            col1, col2, col3 = st.columns([2, 1, 1])

                            with col1:
                                st.markdown(
                                    f"**vs {game['opponent']}**"
                                )
                                st.caption(game_date)

                            with col2:
                                st.write(game["format"])

                            with col3:
                                st.markdown(f"**{game['outcome']}**")

                            if st.button(
                                "Review Game",
                                key=f"review_game_{index}",
                                use_container_width=True,
                            ):
                                st.session_state.selected_game = game
                                st.rerun()

# ---------------- STATISTICS PAGE ----------------

elif st.session_state.page == "statistics":

    st.title("Statistics")
    st.caption("Analyse your saved Chess.com games.")

    # Initialize results-screen state.
    if "statistics_show_results" not in st.session_state:
        st.session_state.statistics_show_results = False

    # ---------------- ANALYSIS SETUP SCREEN ----------------

    if not st.session_state.statistics_show_results:

        st.divider()

        st.caption("Choose which saved games you want to analyse.")

        # Outside the form so changing this immediately updates the UI.
        date_mode = st.selectbox(
            "Date selection",
            ["All saved dates", "Custom date range"],
            key="statistics_date_mode",
        )

        with st.form("statistics_filter_form"):

            username = st.text_input(
                "Chess.com username",
                value=(
                    st.session_state.username
                    or st.session_state.default_username
                ),
                placeholder="Enter Chess.com username",
            )

            selected_format = st.selectbox(
                "Game format",
                ["All formats", "Bullet", "Blitz", "Rapid", "Daily"],
            )

            start_date = None
            end_date = None

            if date_mode == "Custom date range":

                st.caption("Dates are interpreted in UTC.")

                col1, col2 = st.columns(2)

                with col1:
                    start_date = st.date_input(
                        "Start date",
                        value=date(2025, 1, 1),
                        max_value=date.today(),
                    )

                with col2:
                    end_date = st.date_input(
                        "End date",
                        value=date.today(),
                        max_value=date.today(),
                    )

            submitted = st.form_submit_button(
                "Analyse Games",
                type="primary",
                use_container_width=True,
            )

        if submitted:

            if not username.strip():

                st.error("Enter a Chess.com username.")

            elif (
                date_mode == "Custom date range"
                and start_date > end_date
            ):

                st.error("Start date cannot be after end date.")

            else:

                if selected_format == "All formats":
                    selected_formats = [
                        "bullet",
                        "blitz",
                        "rapid",
                        "daily",
                    ]
                else:
                    selected_formats = [
                        selected_format.lower()
                    ]

                # Save analysis settings.
                st.session_state.statistics_filters = {
                    "username": username.strip(),
                    "formats": selected_formats,
                    "start_date": start_date,
                    "end_date": end_date,
                }

                st.session_state.statistics_show_results = True
                st.rerun()

    # ---------------- ANALYSIS RESULTS SCREEN ----------------

    else:

        filters = st.session_state.statistics_filters

        username = filters["username"]
        formats = filters["formats"]

        if st.button("← Back to Analysis Setup"):
            st.session_state.statistics_show_results = False
            st.rerun()

        st.divider()

        st.subheader(f"Analysis for {username}")

        
        # ---------------- LOAD SAVED GAMES ----------------

        all_formats = [
            "bullet",
            "blitz",
            "rapid",
            "daily",
        ]

        with st.spinner("Analysing your saved games..."):

            # Load ALL formats for overall performance.
            all_games = load_games(
                username,
                all_formats,
                5000,
                start_date=filters["start_date"],
                end_date=filters["end_date"],
            )

            # Load only selected formats for the format breakdown.
            selected_games = load_games(
                username,
                formats,
                5000,
                start_date=filters["start_date"],
                end_date=filters["end_date"],
            )

        if not all_games:

            st.warning(
                "No saved games found for this username and period. "
                "Download games from Dashboard first."
            )

        else:

            # ---------------- OVERALL PERFORMANCE ----------------

            st.caption(
                f"Analysing {len(all_games)} saved games across all formats."
            )

            overall_stats = get_game_stats(
                all_games,
                username,
            )

            st.divider()

            show_stats(
                "Overall Performance (All Formats)",
                overall_stats,
            )

            # ---------------- FORMAT BREAKDOWN ----------------

            st.divider()

            st.subheader("Performance by Format")

            if not selected_games:

                st.info("No games found for the selected format.")

            else:

                for game_format in formats:

                    format_games = [
                        item for item in selected_games
                        if item["time_class"] == game_format
                    ]

                    if not format_games:
                        continue

                    format_stats = get_game_stats(
                        format_games,
                        username,
                    )

                    show_stats(
                        game_format.title(),
                        format_stats,
                    )
