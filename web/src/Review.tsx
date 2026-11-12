import { useEffect, useMemo, useState } from "react";
import { api, type Game, type Level, type MoveReview, type Review as ReviewData } from "./api";
import { Board } from "./Board";
import { opponentName, signed } from "./format";
import { replay } from "./geometry";

const LABEL_TEXT: Record<MoveReview["label"], string> = {
  good: "Good",
  okay: "Okay",
  mistake: "Mistake",
};

interface Props {
  game: Game;
  levels: Level[];
  onPlayAgain: () => void;
}

function facts(m: MoveReview): string {
  const parts: string[] = [];
  if (m.boxes_taken) parts.push(`took ${m.boxes_taken} box${m.boxes_taken > 1 ? "es" : ""}`);
  if (m.boxes_given_away)
    parts.push(`gave away ${m.boxes_given_away} box${m.boxes_given_away > 1 ? "es" : ""}`);
  else if (m.left_three_sided) parts.push("left a box with 3 sides");
  return parts.join(", ");
}

export function Review({ game, levels, onPlayAgain }: Props) {
  const [review, setReview] = useState<ReviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState(0); // index into review.moves

  useEffect(() => {
    let live = true;
    setReview(null);
    setError(null);
    api
      .review(game.id)
      .then((r) => {
        if (!live) return;
        setReview(r);
        // Start on the first mistake: that's what people want to see.
        const firstMistake = r.moves.findIndex((m) => m.label === "mistake");
        setSelected(Math.max(firstMistake, 0));
      })
      .catch((e) => live && setError(e instanceof Error ? e.message : String(e)));
    return () => {
      live = false;
    };
  }, [game.id]);

  const count = review?.moves.length ?? 0;
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      if (e.key === "ArrowLeft") setSelected((i) => Math.max(i - 1, 0));
      if (e.key === "ArrowRight") setSelected((i) => Math.min(i + 1, count - 1));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [count]);

  const current = review?.moves[selected];
  // The board right after the reviewed move, so you see what you played and what it left.
  const position = useMemo(
    () => current && replay(game.rows, game.cols, game.moves.slice(0, current.ply + 1)),
    [game, current],
  );

  const you = game.human_player;
  const tally = { good: 0, okay: 0, mistake: 0 };
  review?.moves.forEach((m) => tally[m.label]++);
  const youWon = game.winner === you;

  return (
    <div className="review">
      <header className="review-head">
        <div>
          <h2>Game review</h2>
          <p className="muted">
            {youWon ? "Won" : game.winner === null ? "Drew" : "Lost"}{" "}
            {game.scores[you]}–{game.scores[1 - you]} against{" "}
            {opponentName(game.level, game.bot, levels)} on {game.rows} × {game.cols}
          </p>
        </div>
        <button className="primary" onClick={onPlayAgain}>
          Play again
        </button>
      </header>

      {error && <p className="error">{error}</p>}
      {!review && !error && (
        <p className="status">
          <span className="spinner" /> Analysing your moves… this takes a few seconds.
        </p>
      )}

      {review && review.moves.length === 0 && <p className="muted">You made no moves this game.</p>}

      {review && current && position && (
        <>
          <div className="tally">
            <span className="tag good">{tally.good} good</span>
            <span className="tag okay">{tally.okay} okay</span>
            <span className="tag mistake">
              {tally.mistake} mistake{tally.mistake === 1 ? "" : "s"}
            </span>
          </div>

          <div className="review-body">
            <section className="review-board">
              <Board
                rows={game.rows}
                cols={game.cols}
                position={position}
                humanPlayer={you}
                lastEdge={current.move}
                bestEdge={current.best_move !== current.move ? current.best_move : null}
              />
              <div className="stepper">
                <button onClick={() => setSelected(selected - 1)} disabled={selected === 0}>
                  ← Previous
                </button>
                <span className="muted">
                  Your move {selected + 1} of {count}
                </span>
                <button onClick={() => setSelected(selected + 1)} disabled={selected === count - 1}>
                  Next →
                </button>
              </div>
              <p className="legend">
                <span className="swatch you" /> your move (thick)
                {current.best_move !== current.move && (
                  <>
                    <span className="swatch best" /> better move
                  </>
                )}
              </p>
            </section>

            <section className="panel detail">
              <h3>
                <span className={`tag ${current.label}`}>{LABEL_TEXT[current.label]}</span> Move{" "}
                {selected + 1}
              </h3>
              {facts(current) && <p>You {facts(current)}.</p>}
              {current.explanation && <p className="explanation">{current.explanation}</p>}
              <dl className="values">
                <dt>Your move</dt>
                <dd>{signed(current.score)}</dd>
                <dt>Best move</dt>
                <dd>{signed(current.best_score)}</dd>
              </dl>
              <p className="muted small">
                Values go from −1 (the bot gets every box from here) to +1 (you get every box),
                assuming both sides play well afterwards.
              </p>
            </section>
          </div>

          <ol className="move-list">
            {review.moves.map((m, i) => (
              <li key={m.ply}>
                <button
                  className={i === selected ? "selected" : ""}
                  onClick={() => setSelected(i)}
                >
                  <span className={`dot-tag ${m.label}`} aria-hidden />
                  <span>Move {i + 1}</span>
                  <span className="muted">{facts(m) || LABEL_TEXT[m.label]}</span>
                  {m.explanation && <span className="has-note" title="Has an explanation">💬</span>}
                </button>
              </li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
