
import { useState } from "react";
import { Chess } from "chess.js";
import { Chessboard } from "react-chessboard";
import "./GameReview.css";

function GameReview() {
  const [game, setGame] = useState(() => new Chess());

  // Create a copy while preserving the move history.
  function copyGame() {
    const copy = new Chess();
    const pgn = game.pgn();

    if (pgn) {
      copy.loadPgn(pgn);
    }

    return copy;
  }

  function undoMove() {
    if (game.history().length === 0) return;

    const copy = copyGame();
    copy.undo();
    setGame(copy);
  }

  function resetGame() {
    setGame(new Chess());
  }

  const moves = game.history();

  let status = "White to move";

  if (game.isGameOver()) {
    if (game.isCheckmate()) {
      status = "Checkmate";
    } else if (game.isDraw()) {
      status = "Draw";
    } else {
      status = "Game over";
    }
  } else if (game.isCheck()) {
    status = game.turn() === "w"
      ? "White is in check"
      : "Black is in check";
  } else {
    status = game.turn() === "w"
      ? "White to move"
      : "Black to move";
  }

  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">ANALYSIS WORKSPACE</div>
          <h2>Game Review</h2>
          <p>Explore positions and review your moves.</p>
        </div>
      </div>

      <div className="review-layout">
        <div className="board-panel">
          <div className="board-header">
            <span>ANALYSIS BOARD</span>
            <span className="game-status">{status}</span>
          </div>

          <div className="chessboard-container">
            <Chessboard
              options={{
                id: "game-review-board",
                position: game.fen(),
                boardOrientation: "white",
                showNotation: true,
                onPieceDrop: ({ sourceSquare, targetSquare }) => {
                  if (!targetSquare) return false;

                  const copy = copyGame();

                  try {
                    copy.move({
                      from: sourceSquare,
                      to: targetSquare,
                      promotion: "q",
                    });

                    setGame(copy);
                    return true;
                  } catch {
                    return false;
                  }
                },
              }}
            />
          </div>

          <div className="board-controls">
            <button onClick={undoMove}>↶ Undo</button>
            <button onClick={resetGame}>↻ Reset position</button>
          </div>
        </div>

        <div className="moves-panel">
          <div className="panel-heading">
            <h3>Move history</h3>
            <span>{moves.length} MOVES</span>
          </div>

          {moves.length === 0 ? (
            <div className="moves-empty">
              No moves yet. Make a move on the board.
            </div>
          ) : (
            <div className="move-list">
              {Array.from(
                { length: Math.ceil(moves.length / 2) },
                (_, index) => (
                  <div className="move-row" key={index}>
                    <span className="move-number">
                      {index + 1}.
                    </span>
                    <span>{moves[index * 2]}</span>
                    <span>{moves[index * 2 + 1] ?? ""}</span>
                  </div> ) )} </div> )} </div> </div> </section>);}

export default GameReview;
