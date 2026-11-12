// CONTRACT: mirrors dnb/server/schemas.py. Change both in the same PR.

export interface PlayedMove {
  player: number;
  edge: number;
}

export interface Game {
  id: string;
  rows: number;
  cols: number;
  bot: string;
  level: number | null; // set when the game was started from a difficulty level
  human_player: number;
  current_player: number;
  moves: PlayedMove[];
  box_owners: number[]; // -1 = unclaimed
  scores: number[];
  is_over: boolean;
  winner: number | null;
}

export interface Level {
  level: number;
  name: string;
  bot: string; // bot spec behind the level
  available: boolean; // false until the bot behind the level is implemented
}

export interface PlayerStats {
  player_id: string;
  games_played: number;
  win_rate: number;
  boxes_given_away_per_game: number;
  rating: number;
  level: number; // the level the adjuster recommends next ("Auto" in the picker uses it)
}

export interface GameSummary {
  id: string;
  bot: string;
  level: number | null;
  rows: number;
  cols: number;
  score_human: number;
  score_bot: number;
  result: number; // for the human: 1 win, 0.5 draw, 0 loss
  finished_at: string; // UTC, "YYYY-MM-DD HH:MM:SS"
}

export interface Hint {
  move: number;
  score: number; // [-1, 1], higher is better for the player to move
}

export interface Danger {
  edges: number[]; // legal moves that would leave a box with 3 sides
}

export interface MoveReview {
  ply: number; // index into Game.moves
  move: number;
  best_move: number; // same as move when the played move ties for best
  score: number;
  best_score: number;
  label: "good" | "okay" | "mistake";
  boxes_taken: number;
  boxes_given_away: number;
  left_three_sided: boolean;
  explanation: string | null; // only the 2-3 biggest mistakes have one
}

export interface Review {
  game_id: string;
  moves: MoveReview[]; // the human's moves only
}

export interface NewGameRequest {
  rows?: number;
  cols?: number;
  bot?: string; // ignored when level is set
  level?: number | null;
  human_first?: boolean;
  player_id?: string;
}

/** An error response from the API. `status` 501 means a teammate's part isn't shipped yet. */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : null;
    throw new ApiError(detail ?? `${res.status} ${res.statusText}`, res.status);
  }
  return res.json();
}

export const api = {
  listBots: () => request<string[]>("/bots"),
  listLevels: () => request<Level[]>("/levels"),
  newGame: (req: NewGameRequest) =>
    request<Game>("/games", { method: "POST", body: JSON.stringify(req) }),
  move: (id: string, edge: number) =>
    request<Game>(`/games/${id}/move`, { method: "POST", body: JSON.stringify({ edge }) }),
  getGame: (id: string) => request<Game>(`/games/${id}`),
  hint: (id: string) => request<Hint>(`/games/${id}/hint`),
  danger: (id: string) => request<Danger>(`/games/${id}/danger`),
  review: (id: string) => request<Review>(`/games/${id}/review`),
  playerGames: (playerId: string, limit = 20) =>
    request<GameSummary[]>(`/players/${encodeURIComponent(playerId)}/games?limit=${limit}`),
  stats: (playerId: string) =>
    request<PlayerStats>(`/players/${encodeURIComponent(playerId)}/stats`),
};
