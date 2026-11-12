import type { GameSummary, Level, PlayerStats } from "./api";
import { opponentName, percent, resultWord } from "./format";

interface Props {
  playerId: string;
  levels: Level[];
  stats: PlayerStats | null;
  statsNote: string | null; // why stats are missing, e.g. not implemented yet
  history: GameSummary[];
  onOpenReview: (gameId: string) => void;
}

/** Recent games are listed in local time; the server stores UTC. */
function when(finishedAt: string): string {
  const d = new Date(`${finishedAt.replace(" ", "T")}Z`);
  return Number.isNaN(d.getTime())
    ? finishedAt
    : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function Profile({ playerId, levels, stats, statsNote, history, onOpenReview }: Props) {
  // Until Person 3's stats ship, show what the history alone can tell.
  const wins = history.filter((g) => g.result === 1).length;
  const draws = history.filter((g) => g.result === 0.5).length;

  return (
    <div className="profile">
      <h2>{playerId}</h2>

      {stats ? (
        <div className="tiles">
          <Tile label="Rating" value={Math.round(stats.rating).toString()} />
          <Tile label="Games played" value={stats.games_played.toString()} />
          <Tile label="Win rate" value={percent(stats.win_rate)} />
          <Tile
            label="Boxes given away per game"
            value={stats.boxes_given_away_per_game.toFixed(1)}
          />
          <Tile
            label="Recommended level"
            value={`${stats.level} · ${opponentName(stats.level, "", levels)}`}
          />
        </div>
      ) : (
        <>
          <div className="tiles">
            <Tile label="Recent games" value={history.length.toString()} />
            <Tile
              label="Recent win rate"
              value={history.length ? percent((wins + draws / 2) / history.length) : "–"}
            />
          </div>
          {statsNote && <p className="muted small">{statsNote}</p>}
        </>
      )}

      <h3>Recent games</h3>
      {history.length === 0 ? (
        <p className="muted">No finished games yet. Play one!</p>
      ) : (
        <table className="history">
          <thead>
            <tr>
              <th>When</th>
              <th>Opponent</th>
              <th>Board</th>
              <th>Score</th>
              <th>Result</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {history.map((g) => (
              <tr key={g.id}>
                <td>{when(g.finished_at)}</td>
                <td>{opponentName(g.level, g.bot, levels)}</td>
                <td>
                  {g.rows} × {g.cols}
                </td>
                <td>
                  {g.score_human}–{g.score_bot}
                </td>
                <td>
                  <span className={`tag ${resultWord(g.result).toLowerCase()}`}>
                    {resultWord(g.result)}
                  </span>
                </td>
                <td>
                  <button className="link" onClick={() => onOpenReview(g.id)}>
                    Review
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="tile">
      <span className="tile-value">{value}</span>
      <span className="tile-label">{label}</span>
    </div>
  );
}
