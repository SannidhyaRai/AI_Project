import { useEffect, useMemo, useState } from "react";
import { ApiError, api, type Game, type Level } from "./api";
import { Board } from "./Board";
import { opponentName } from "./format";
import { replay } from "./geometry";
import { useStored } from "./useStored";

const BOT_MOVE_DELAY_MS = 380; // bot moves are shown one at a time, so you can follow them
const SIZES = [2, 3, 4, 5];

type Choice = number | "auto" | "custom";

interface Props {
  playerId: string;
  levels: Level[];
  bots: string[];
  autoLevel: number | null; // from player stats; null until Person 3 ships them
  onGameOver: (game: Game) => void;
  onReview: (game: Game) => void;
}

/** The level "Auto" plays: the recommended one, or the nearest playable level below it. */
function resolveAuto(levels: Level[], recommended: number | null): number | null {
  if (recommended === null) return null;
  const playable = levels.filter((l) => l.available);
  const below = playable.filter((l) => l.level <= recommended);
  return (below.at(-1) ?? playable[0])?.level ?? null;
}

export function Play({ playerId, levels, bots, autoLevel, onGameOver, onReview }: Props) {
  const [choice, setChoice] = useStored<Choice>("choice", 2);
  const [customBot, setCustomBot] = useStored("customBot", "greedy");
  const [size, setSize] = useStored("size", 3);
  const [humanFirst, setHumanFirst] = useStored("humanFirst", true);
  const [showDanger, setShowDanger] = useStored("showDanger", true);

  const [game, setGame] = useState<Game | null>(null);
  const [shown, setShown] = useState(0); // how many of game.moves are on the board so far
  const [pending, setPending] = useState<number | null>(null); // your move, before the server answers
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hint, setHint] = useState<{ ply: number; edge: number } | null>(null);
  const [hintLoading, setHintLoading] = useState(false);
  const [hintsUsed, setHintsUsed] = useState(0);
  const [danger, setDanger] = useState<{ ply: number; edges: Set<number> } | null>(null);

  const autoResolved = resolveAuto(levels, autoLevel);
  const chosenLevel = levels.find((l) => l.level === choice);
  const canStart =
    !busy &&
    (choice === "custom" ||
      (choice === "auto" ? autoResolved !== null : chosenLevel?.available === true));

  // Reveal moves one by one: yours at once, the bot's with a short pause each.
  useEffect(() => {
    if (!game || shown >= game.moves.length) return;
    const next = game.moves[shown];
    const delay = next.player === game.human_player ? 0 : BOT_MOVE_DELAY_MS;
    const t = setTimeout(() => setShown(shown + 1), delay);
    return () => clearTimeout(t);
  }, [game, shown]);

  const animating = !!game && shown < game.moves.length;
  const finished = !!game && game.is_over && !animating;
  const yourTurn =
    !!game && !busy && !animating && !game.is_over && game.current_player === game.human_player;
  const ply = game?.moves.length ?? 0;

  useEffect(() => {
    if (finished && game) onGameOver(game);
    // Once per game: onGameOver refreshes stats and history.
  }, [finished, game?.id]);

  // Danger lines are cheap to compute, so fetch them on every one of your turns.
  useEffect(() => {
    if (!game || !yourTurn || !showDanger) return;
    let live = true;
    api
      .danger(game.id)
      .then((d) => live && setDanger({ ply: game.moves.length, edges: new Set(d.edges) }))
      .catch(() => live && setDanger(null));
    return () => {
      live = false;
    };
  }, [game, yourTurn, showDanger]);

  const position = useMemo(
    () => (game ? replay(game.rows, game.cols, game.moves.slice(0, shown)) : null),
    [game, shown],
  );

  async function startGame() {
    setBusy(true);
    setError(null);
    try {
      const level = choice === "custom" ? null : choice === "auto" ? autoResolved : choice;
      const g = await api.newGame({
        rows: size,
        cols: size,
        level,
        bot: customBot,
        human_first: humanFirst,
        player_id: playerId,
      });
      setGame(g);
      setShown(0);
      setPending(null);
      setHint(null);
      setHintsUsed(0);
      setDanger(null);
    } catch (e) {
      setError(
        e instanceof ApiError && e.status === 501
          ? `${e.message}. Pick another level for now.`
          : e instanceof Error
            ? e.message
            : String(e),
      );
    } finally {
      setBusy(false);
    }
  }

  async function move(edge: number) {
    if (!game) return;
    setBusy(true);
    setError(null);
    setPending(edge);
    try {
      setGame(await api.move(game.id, edge));
    } catch (e) {
      setPending(null);
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function askHint() {
    if (!game) return;
    setHintLoading(true);
    setError(null);
    try {
      const h = await api.hint(game.id);
      setHint({ ply: game.moves.length, edge: h.move });
      setHintsUsed((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setHintLoading(false);
    }
  }

  const you = game?.human_player ?? 0;
  const scores = position?.scores ?? [0, 0];
  // Whose turn the board shows: during the animation, whoever makes the next shown move.
  const turn = game ? (animating ? game.moves[shown].player : game.current_player) : null;
  const lastShown = game && shown > 0 ? game.moves[shown - 1] : null;
  const opponent = game ? opponentName(game.level, game.bot, levels) : "";

  let status: string;
  if (!game) status = "Pick a difficulty and start a game.";
  else if (busy) status = "Bot is thinking…";
  else if (animating) status = "Bot is moving…";
  else if (game.is_over)
    status =
      game.winner === null ? "It's a draw!" : game.winner === you ? "You win!" : "The bot wins.";
  else if (lastShown && lastShown.player === you && shown > 0) status = "Box! You move again.";
  else status = "Your move.";

  return (
    <div className="play">
      <aside className="panel setup">
        <h2>New game</h2>
        <fieldset>
          <legend>Difficulty</legend>
          <div className="levels">
            {levels.map((l) => (
              <button
                key={l.level}
                className={choice === l.level ? "chip selected" : "chip"}
                disabled={!l.available}
                title={l.available ? l.bot : `${l.bot}: not implemented yet`}
                onClick={() => setChoice(l.level)}
              >
                <span className="chip-num">{l.level}</span> {l.name}
              </button>
            ))}
            <button
              className={choice === "auto" ? "chip selected" : "chip"}
              disabled={autoResolved === null}
              title={
                autoResolved === null
                  ? "Needs player stats (coming with the difficulty system)"
                  : `Picks level ${autoResolved} from your results`
              }
              onClick={() => setChoice("auto")}
            >
              Auto{autoResolved !== null && ` (${autoResolved})`}
            </button>
          </div>
          <details open={choice === "custom"}>
            <summary>Pick a bot yourself</summary>
            <label className="row">
              <input
                type="radio"
                checked={choice === "custom"}
                onChange={() => setChoice("custom")}
              />
              <input
                list="bot-names"
                value={customBot}
                onChange={(e) => {
                  setCustomBot(e.target.value);
                  setChoice("custom");
                }}
                placeholder="minimax:depth=3"
                aria-label="Bot spec"
              />
              <datalist id="bot-names">
                {bots.map((b) => (
                  <option key={b} value={b} />
                ))}
              </datalist>
            </label>
          </details>
        </fieldset>

        <label className="row">
          Board
          <select value={size} onChange={(e) => setSize(Number(e.target.value))}>
            {SIZES.map((n) => (
              <option key={n} value={n}>
                {n} × {n} boxes
              </option>
            ))}
          </select>
        </label>
        <label className="row">
          Who starts
          <select
            value={humanFirst ? "you" : "bot"}
            onChange={(e) => setHumanFirst(e.target.value === "you")}
          >
            <option value="you">You</option>
            <option value="bot">Bot</option>
          </select>
        </label>
        <button className="primary" onClick={startGame} disabled={!canStart}>
          {game && !finished ? "Restart" : "Start game"}
        </button>
      </aside>

      <section className="table">
        <div className="scoreboard">
          <div className={`player you ${turn === you && !game?.is_over ? "active" : ""}`}>
            <span className="who">You</span>
            <span className="score">{scores[you]}</span>
          </div>
          <div className={`player bot ${turn === 1 - you && !game?.is_over ? "active" : ""}`}>
            <span className="who">Bot{game && <small> · {opponent}</small>}</span>
            <span className="score">{scores[1 - you]}</span>
          </div>
        </div>

        <p className="status" aria-live="polite">
          {status}
        </p>
        {error && <p className="error">{error}</p>}

        {game && position && (
          <Board
            rows={game.rows}
            cols={game.cols}
            position={position}
            humanPlayer={you}
            canMove={yourTurn}
            onMove={move}
            lastEdge={lastShown?.edge ?? null}
            pendingEdge={pending}
            hintEdge={yourTurn && hint?.ply === ply ? hint.edge : null}
            dangerEdges={showDanger && yourTurn && danger?.ply === ply ? danger.edges : undefined}
          />
        )}

        {game && !finished && (
          <div className="actions">
            <button onClick={askHint} disabled={!yourTurn || hintLoading}>
              {hintLoading ? "Thinking…" : "Hint"}
            </button>
            <label className="toggle">
              <input
                type="checkbox"
                checked={showDanger}
                onChange={(e) => setShowDanger(e.target.checked)}
              />
              Show risky lines
            </label>
            {hintsUsed > 0 && <span className="muted">Hints used: {hintsUsed}</span>}
          </div>
        )}

        {finished && game && (
          <div className={`banner ${game.winner === null ? "draw" : game.winner === you ? "win" : "loss"}`}>
            <strong>{status}</strong> {scores[you]}–{scores[1 - you]} against {opponent}
            {hintsUsed > 0 && `, with ${hintsUsed} hint${hintsUsed > 1 ? "s" : ""}`}.
            <div className="banner-actions">
              <button className="primary" onClick={() => onReview(game)}>
                Review my moves
              </button>
              <button onClick={startGame} disabled={!canStart}>
                Play again
              </button>
            </div>
          </div>
        )}

        {game && showDanger && !finished && (
          <p className="legend">
            <span className="swatch danger" /> risky: leaves a box with 3 sides
            <span className="swatch hint" /> hint
          </p>
        )}
      </section>
    </div>
  );
}
