import { useCallback, useEffect, useState } from "react";
import { ApiError, api, type Game, type GameSummary, type Level, type PlayerStats } from "./api";
import { Play } from "./Play";
import { Profile } from "./Profile";
import { Review } from "./Review";
import { useStored } from "./useStored";

type Tab = "play" | "review" | "profile";

export default function App() {
  const [playerId, setPlayerId] = useStored("player", "guest");
  const [nameDraft, setNameDraft] = useState(playerId);
  const [tab, setTab] = useState<Tab>("play");
  const [levels, setLevels] = useState<Level[]>([]);
  const [bots, setBots] = useState<string[]>([]);
  const [stats, setStats] = useState<PlayerStats | null>(null);
  const [statsNote, setStatsNote] = useState<string | null>(null);
  const [history, setHistory] = useState<GameSummary[]>([]);
  const [reviewGame, setReviewGame] = useState<Game | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.listLevels(), api.listBots()])
      .then(([l, b]) => {
        setLevels(l);
        setBots(b);
      })
      .catch((e) => setError(`Can't reach the server: ${e instanceof Error ? e.message : e}`));
  }, []);

  const refreshPlayer = useCallback(() => {
    api
      .stats(playerId)
      .then((s) => {
        setStats(s);
        setStatsNote(null);
      })
      .catch((e) => {
        setStats(null);
        setStatsNote(
          e instanceof ApiError && e.status === 501
            ? "Rating, level advice and detailed stats appear once the difficulty system is in."
            : `Stats unavailable: ${e instanceof Error ? e.message : e}`,
        );
      });
    api
      .playerGames(playerId)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [playerId]);

  useEffect(refreshPlayer, [refreshPlayer]);

  function commitName() {
    const name = nameDraft.trim().slice(0, 40);
    if (name) setPlayerId(name);
    else setNameDraft(playerId);
  }

  function openReview(game: Game) {
    setReviewGame(game);
    setTab("review");
  }

  async function openSavedReview(gameId: string) {
    try {
      openReview(await api.getGame(gameId));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  return (
    <>
      <header className="top">
        <h1>
          Dots and Boxes <span className="accent">AI</span>
        </h1>
        <nav>
          <button className={tab === "play" ? "tab active" : "tab"} onClick={() => setTab("play")}>
            Play
          </button>
          <button
            className={tab === "review" ? "tab active" : "tab"}
            onClick={() => setTab("review")}
            disabled={!reviewGame}
          >
            Review
          </button>
          <button
            className={tab === "profile" ? "tab active" : "tab"}
            onClick={() => setTab("profile")}
          >
            Profile
          </button>
        </nav>
        <label className="player-name">
          Playing as
          <input
            value={nameDraft}
            maxLength={40}
            onChange={(e) => setNameDraft(e.target.value)}
            onBlur={commitName}
            onKeyDown={(e) => e.key === "Enter" && e.currentTarget.blur()}
          />
        </label>
      </header>

      <main>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        {/* Play stays mounted while you look at other tabs, so a game in progress isn't lost. */}
        <div hidden={tab !== "play"}>
          <Play
            playerId={playerId}
            levels={levels}
            bots={bots}
            autoLevel={stats?.level ?? null}
            onGameOver={refreshPlayer}
            onReview={openReview}
          />
        </div>
        {tab === "review" && reviewGame && (
          <Review game={reviewGame} levels={levels} onPlayAgain={() => setTab("play")} />
        )}
        {tab === "profile" && (
          <Profile
            playerId={playerId}
            levels={levels}
            stats={stats}
            statsNote={statsNote}
            history={history}
            onOpenReview={openSavedReview}
          />
        )}
      </main>
    </>
  );
}
