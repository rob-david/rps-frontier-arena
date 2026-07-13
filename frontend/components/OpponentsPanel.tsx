import { OPPONENT_IDS, PLAYER_DEFS, type CheckedOpponents, type OpponentId } from "@/lib/game";

interface OpponentsPanelProps {
  checkedOpponents: CheckedOpponents;
  isLocked: boolean;
  onToggleOpponent: (id: OpponentId) => void;
}

export default function OpponentsPanel({ checkedOpponents, isLocked, onToggleOpponent }: OpponentsPanelProps) {
  return (
    <div className="opponents-panel">
      <div className="opponents-title">Opponents</div>
      <div className="opponents-list">
        {OPPONENT_IDS.map((id) => {
          const player = PLAYER_DEFS.find((candidate) => candidate.id === id);
          if (!player) {
            return null;
          }

          const isChecked = checkedOpponents[id];
          return (
            <label
              key={id}
              className={`opp-toggle ${id}${isChecked ? " checked" : ""}${isLocked ? " locked" : ""}`}
              onClick={(event) => {
                event.preventDefault();
                if (isLocked) {
                  return;
                }
                onToggleOpponent(id);
              }}
              aria-disabled={isLocked}
            >
              <input type="checkbox" checked={isChecked} readOnly />
              <span className="box">{isChecked ? "✓" : ""}</span>
              <span className="lbl">{player.name}</span>
            </label>
          );
        })}
      </div>
      <div className="opponents-hint">Fewer opponents = fewer ties. Pick who plays today.</div>
    </div>
  );
}
