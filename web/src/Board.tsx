import { edgeGeom, numEdges, type Position } from "./geometry";

const GAP = 70; // pixels between dots
const PAD = 20;

interface Props {
  rows: number;
  cols: number;
  position: Position;
  humanPlayer: number; // colours follow who you are, not player 0/1
  canMove?: boolean;
  onMove?: (edge: number) => void;
  lastEdge?: number | null; // drawn thicker
  pendingEdge?: number | null; // your move, shown while the server answers
  hintEdge?: number | null; // pulsing suggestion
  dangerEdges?: ReadonlySet<number>; // undrawn lines that give a box away
  bestEdge?: number | null; // review: the better move, dashed
}

export function Board({
  rows,
  cols,
  position,
  humanPlayer,
  canMove = false,
  onMove,
  lastEdge = null,
  pendingEdge = null,
  hintEdge = null,
  dangerEdges,
  bestEdge = null,
}: Props) {
  const px = (v: number) => PAD + v * GAP;
  const role = (player: number) => (player === humanPlayer ? "you" : "bot");

  return (
    <svg
      className={canMove ? "board can-move" : "board"}
      viewBox={`0 0 ${2 * PAD + cols * GAP} ${2 * PAD + rows * GAP}`}
      role="img"
      aria-label={`Dots and Boxes board, ${rows} by ${cols} boxes`}
    >
      {position.owners.map((owner, b) =>
        owner < 0 ? null : (
          <g key={`box-${b}`} className={`box ${role(owner)}`}>
            <rect
              x={px(b % cols) + 7}
              y={px(Math.floor(b / cols)) + 7}
              width={GAP - 14}
              height={GAP - 14}
              rx={7}
            />
            <text x={px(b % cols) + GAP / 2} y={px(Math.floor(b / cols)) + GAP / 2}>
              {owner === humanPlayer ? "You" : "Bot"}
            </text>
          </g>
        ),
      )}

      {Array.from({ length: numEdges(rows, cols) }, (_, e) => {
        const g = edgeGeom(rows, cols, e);
        const line = { x1: px(g.x1), y1: px(g.y1), x2: px(g.x2), y2: px(g.y2) };
        const player = position.drawnBy.get(e);
        const drawn = player !== undefined;
        const pending = !drawn && e === pendingEdge;

        const classes = ["edge"];
        if (drawn) classes.push("drawn", role(player));
        else if (pending) classes.push("drawn", "you", "pending");
        else if (e === hintEdge) classes.push("hint");
        else if (dangerEdges?.has(e)) classes.push("danger");
        if (e === lastEdge) classes.push("last");

        return (
          <g key={`edge-${e}`}>
            {e === lastEdge && drawn && (
              // Soft glow so the latest (or reviewed) move is easy to spot.
              <line {...line} className={`edge-halo ${role(player)}`} />
            )}
            <line {...line} className={classes.join(" ")} />
            {e === bestEdge && <line {...line} className="edge best" />}
            {!drawn && !pending && canMove && onMove && (
              // Wide invisible hit area so lines are easy to click or tap.
              <line {...line} className="edge-hit" onClick={() => onMove(e)}>
                <title>{dangerEdges?.has(e) ? "Gives the bot a free box" : "Draw this line"}</title>
              </line>
            )}
          </g>
        );
      })}

      {Array.from({ length: (rows + 1) * (cols + 1) }, (_, d) => (
        <circle
          key={`dot-${d}`}
          cx={px(d % (cols + 1))}
          cy={px(Math.floor(d / (cols + 1)))}
          r={6}
          className="dot"
        />
      ))}
    </svg>
  );
}
