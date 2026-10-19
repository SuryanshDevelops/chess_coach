
import chess
import chess.pgn


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


def analyze_pgn(file_path):
    """Read a PGN and report each move's clock information."""

    with open(file_path, "r", encoding="utf-8") as pgn_file:
        game = chess.pgn.read_game(pgn_file)

    if game is None:
        print("No valid chess game found in the PGN file.")
        return

    time_control = game.headers.get("TimeControl", "")
    starting_clock, increment = parse_starting_clock(time_control)

    # Store the previous clock separately for White and Black.
    previous_clock = {
        chess.WHITE: starting_clock,
        chess.BLACK: starting_clock,
    }

    board = game.board()

    print(f"\nGame: {game.headers.get('Event', 'Unknown')}")
    print(f"White: {game.headers.get('White', 'Unknown')}")
    print(f"Black: {game.headers.get('Black', 'Unknown')}")
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

        # Convert the move into readable chess notation.
        move_san = board.san(node.move)

        # Clock annotation: remaining time after this move.
        clock_left = node.clock()

        # Exact elapsed time, if the PGN supplies [%emt].
        elapsed = node.emt()

        if elapsed is None and clock_left is not None:
            old_clock = previous_clock[color]

            if old_clock is not None:
                elapsed = old_clock + increment - clock_left

        # Reject impossible negative times caused by missing
        # or inconsistent clock data.
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

    print("-" * 76)
    print("PGN analysis complete.")


if __name__ == "__main__":
    analyze_pgn("chess_games.pgn")
