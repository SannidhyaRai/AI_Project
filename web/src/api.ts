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
  human_player: number;
  current_player: number;
  moves: PlayedMove[];
  box_owners: number[]; // -1 = unclaimed
  scores: number[];
  is_over: boolean;
  winner: number | null;
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
  bot?: string;
  level?: number | null;
  human_first?: boolean;
  player_id?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  listBots: () => request<string[]>("/bots"),
  newGame: (req: NewGameRequest) =>
    request<Game>("/games", { method: "POST", body: JSON.stringify(req) }),
  move: (id: string, edge: number) =>
    request<Game>(`/games/${id}/move`, { method: "POST", body: JSON.stringify({ edge }) }),
  hint: (id: string) => request<Hint>(`/games/${id}/hint`),
  danger: (id: string) => request<Danger>(`/games/${id}/danger`),
  review: (id: string) => request<Review>(`/games/${id}/review`),
  // TODO(P5): stats once Person 3 ships it.
};
