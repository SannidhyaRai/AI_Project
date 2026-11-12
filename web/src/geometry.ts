// Same edge numbering as dnb/engine/state.py: horizontal edges first, then vertical.

export interface EdgeGeom {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export function numEdges(rows: number, cols: number): number {
  return (rows + 1) * cols + rows * (cols + 1);
}

/** Edge index -> endpoints in dot coordinates (column, row). */
export function edgeGeom(rows: number, cols: number, edge: number): EdgeGeom {
  const numH = (rows + 1) * cols;
  if (edge < numH) {
    const r = Math.floor(edge / cols);
    const c = edge % cols;
    return { x1: c, y1: r, x2: c + 1, y2: r };
  }
  const k = edge - numH;
  const r = Math.floor(k / (cols + 1));
  const c = k % (cols + 1);
  return { x1: c, y1: r, x2: c, y2: r + 1 };
}

/** Box index -> its four edges (top, bottom, left, right), as in dnb/engine/state.py. */
export function boxEdges(rows: number, cols: number, box: number): [number, number, number, number] {
  const numH = (rows + 1) * cols;
  const r = Math.floor(box / cols);
  const c = box % cols;
  return [
    r * cols + c,
    (r + 1) * cols + c,
    numH + r * (cols + 1) + c,
    numH + r * (cols + 1) + c + 1,
  ];
}

export interface Position {
  drawnBy: Map<number, number>; // edge -> player who drew it
  owners: number[]; // box -> player, -1 = unclaimed
  scores: [number, number];
}

/**
 * The board after the given moves. The server is the source of truth for rules; this only
 * rebuilds earlier positions for display (animating bot moves, stepping through the review).
 */
export function replay(
  rows: number,
  cols: number,
  moves: readonly { player: number; edge: number }[],
): Position {
  const drawnBy = new Map<number, number>();
  const owners: number[] = Array(rows * cols).fill(-1);
  const scores: [number, number] = [0, 0];
  for (const { player, edge } of moves) {
    drawnBy.set(edge, player);
    for (let b = 0; b < owners.length; b++) {
      if (owners[b] < 0 && boxEdges(rows, cols, b).every((e) => drawnBy.has(e))) {
        owners[b] = player;
        scores[player] += 1;
      }
    }
  }
  return { drawnBy, owners, scores };
}
