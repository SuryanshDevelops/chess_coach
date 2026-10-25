
import chess
import chess.pgn


def describe_game_ending(game, board):
    """Describe the result using the final position and PGN headers."""

    result = game.headers.get("Result", "*")
    termination = game.headers.get("Termination", "").strip()
    termination_lower = termination.lower()

    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        reason = f"Checkmate. {winner} won."

    elif board.is_stalemate():
        reason = "Stalemate. The game is a draw."

    elif board.is_insufficient_material():
        reason = "Draw: insufficient mating material."

    elif board.is_seventyfive_moves():
        reason = "Draw: the 75-move rule."

    elif board.is_fivefold_repetition():
        reason = "Draw: fivefold repetition."

    elif ("time forfeit" in termination_lower
    or "won on time" in termination_lower):
        if result == "1-0":
            reason = "White won on time."
        elif result == "0-1":
            reason = "Black won on time."
        elif result == "1/2-1/2":
            reason = "Draw recorded after a time-forfeit ending."
        else:
            reason = "Time-forfeit ending recorded; winner unknown."

    elif result == "1-0":
        reason = "White won. Exact ending not established."

    elif result == "0-1":
        reason = "Black won. Exact ending not established."

    elif result == "1/2-1/2":
        reason = "Draw. Exact reason not established."

    else:
        reason = "Game unfinished or result not recorded."

    print("\nGAME RESULT")
    print("-" * 40)
    if result == "1-0":
         result_text = "White won"
    elif result == "0-1":
           result_text = "Black won"
    elif result == "1/2-1/2":
      result_text = "Draw"
    else:
      result_text = "Unfinished or unknown"
    print(f"Result: {result_text}")
    print(f"Reason: {reason}")

def parse_starting_clock(time_control):
    """Extract the initial clock and increment from a PGN header."""
    if not time_control or time_control == "-":
        return None, 0.0

    try:
        base, increment = time_control.split("+", 1)
        return float(base), float(increment)
    except ValueError:
        try:
            return float(time_control), 0.0
        except ValueError:
            return None, 0.0



def analyze_game(game):
    """Print the detailed clock report for one game."""

    time_control = game.headers.get("TimeControl", "")
    starting_clock, increment = parse_starting_clock(time_control)

    previous_clock = {
        chess.WHITE: starting_clock,
        chess.BLACK: starting_clock,
    }

    board = game.board()

    print(f"\nGame: {game.headers.get('Event', 'Unknown')}")
    print(f"Date: {game.headers.get('Date', 'Unknown')}")
    print(f"White: {game.headers.get('White', 'Unknown')}")
    print(f"White rating: {game.headers.get('WhiteElo', 'Unknown')}")
    print(f"Black: {game.headers.get('Black', 'Unknown')}")
    print(f"Black rating: {game.headers.get('BlackElo', 'Unknown')}")
    print(f"Time control: {time_control or 'Unknown'}")
    print("-" * 76)

    print(
        f"{'Move':<7}{'Player':<9}{'Played':<10}"
        f"{'Clock left':<14}{'Think time':<14}"
    )
    print("-" * 76)

    for node in game.mainline():
        move_number = board.fullmove_number
        player = "White" if board.turn == chess.WHITE else "Black"
        color = board.turn

        move_san = board.san(node.move)
        clock_left = node.clock()
        elapsed = node.emt()

        if elapsed is None and clock_left is not None:
            old_clock = previous_clock[color]

            if old_clock is not None:
                elapsed = old_clock + increment - clock_left

        if elapsed is not None and elapsed < 0:
            elapsed = None

        clock_text = (
            f"{clock_left:.1f}s"
            if clock_left is not None
            else "Unknown"
        )

        think_text = (
            f"{elapsed:.1f}s"
            if elapsed is not None
            else "Unknown"
        )

        print(
            f"{move_number:<7}{player:<9}{move_san:<10}"
            f"{clock_text:<14}{think_text:<14}"
        )

        if clock_left is not None:
            previous_clock[color] = clock_left

        board.push(node.move)

    describe_game_ending(game, board)
    print("\nGame analysis complete.")


def get_game_summary(game, username):
    """Return a compact summary of one game."""

    white = game.headers.get("White", "Unknown")
    black = game.headers.get("Black", "Unknown")
    result = game.headers.get("Result", "*")

    if white.lower() == username.lower():
        opponent = black
        user_is_white = True
    elif black.lower() == username.lower():
        opponent = white
        user_is_white = False
    else:
        opponent = "Username not found"
        user_is_white = None

    if user_is_white is None:
        outcome = "Unknown"
    elif result == "1/2-1/2":
        outcome = "Draw"
    elif result == "*":
        outcome = "Unfinished"
    elif (result == "1-0") == user_is_white:
        outcome = "Won"
    else:
        outcome = "Lost"

    return {
        "date": game.headers.get("Date", "Unknown"),
        "opponent": opponent,
        "outcome": outcome,
        "white_rating": game.headers.get("WhiteElo", "?"),
        "black_rating": game.headers.get("BlackElo", "?"),
        "time_control": game.headers.get("TimeControl", "?"),
        "moves": len(list(game.mainline_moves())),
    }


def analyze_pgn(file_path):
    """Read games, show a summary, and let the user select a report."""

    games = []

    with open(file_path, "r", encoding="utf-8") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)

            if game is None:
                break

            games.append(game)

    if not games:
        print("No valid chess games found in the PGN file.")
        return

    username = input("Your Chess.com username: ").strip()

    if not username:
        print("Username cannot be empty.")
        return

    opponent_filter = input(
        "Filter by opponent username, or press Enter for all games: "
    ).strip()

    if opponent_filter:
        games = [
            game for game in games
            if (
                game.headers.get("White", "").lower()
                == username.lower()
                and game.headers.get("Black", "").lower()
                == opponent_filter.lower()
            )
            or (
                game.headers.get("Black", "").lower()
                == username.lower()
                and game.headers.get("White", "").lower()
                == opponent_filter.lower()
            )
        ]

    if not games:
        print("No games matched that opponent filter.")
        return

    summaries = [
        get_game_summary(game, username)
        for game in games
    ]

    wins = sum(s["outcome"] == "Won" for s in summaries)
    losses = sum(s["outcome"] == "Lost" for s in summaries)
    draws = sum(s["outcome"] == "Draw" for s in summaries)
    unfinished = sum(
        s["outcome"] in ("Unknown", "Unfinished")
        for s in summaries
    )

    print("\n" + "=" * 76)
    print("CHESS COACH - SESSION OVERVIEW")
    print("=" * 76)
    print(f"Games found: {len(games)}")
    print(f"Wins: {wins} | Losses: {losses} | Draws: {draws}")
    print(f"Unfinished/unknown: {unfinished}")

    print("\nGAME LIST")
    print("-" * 100)
    print(
        f"{'No.':<5}{'Date':<13}{'Opponent':<24}"
        f"{'Result':<13}{'Ratings W/B':<17}{'Moves':<8}"
        f"{'Time control':<12}"
    )
    print("-" * 100)

    for number, summary in enumerate(summaries, start=1):
        ratings = (
            f"{summary['white_rating']}/"
            f"{summary['black_rating']}"
        )

        print(
            f"{number:<5}"
            f"{summary['date']:<13}"
            f"{summary['opponent'][:23]:<24}"
            f"{summary['outcome']:<13}"
            f"{ratings:<17}"
            f"{summary['moves']:<8}"
            f"{summary['time_control']:<12}"
        )

    while True:
        choice = input(
            "\nEnter a game number for its detailed report, "
            "or Q to quit: "
        ).strip()

        if choice.lower() == "q":
            print("Session complete.")
            break

        if not choice.isdigit():
            print("Enter a game number or Q.")
            continue

        game_number = int(choice)

        if not 1 <= game_number <= len(games):
            print("That game number is not in the list.")
            continue

        print(f"\nDETAILED REPORT: GAME {game_number}")
        analyze_game(games[game_number - 1])


if __name__ == "__main__":
    analyze_pgn("chess_games.pgn")


if __name__ == "__main__":
    analyze_pgn("chess_games.pgn")
