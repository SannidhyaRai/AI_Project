import type { Level } from "./api";

/** "Medium" for a level game, the raw bot spec for a custom one. */
export function opponentName(level: number | null, bot: string, levels: Level[]): string {
  if (level !== null) return levels.find((l) => l.level === level)?.name ?? `Level ${level}`;
  return bot;
}

export function resultWord(result: number): "Win" | "Draw" | "Loss" {
  return result === 1 ? "Win" : result === 0.5 ? "Draw" : "Loss";
}

export function percent(x: number): string {
  return `${Math.round(x * 100)}%`;
}

/** Bot scores are in [-1, 1]; show them signed with two decimals. */
export function signed(x: number): string {
  const s = x.toFixed(2);
  return x > 0 ? `+${s}` : s === "-0.00" ? "0.00" : s;
}
