import { currentPlayerDefs, type CheckedOpponents, type ScoreMap } from "@/lib/game";
import { Fragment } from "react";

interface ScoreboardProps {
  checkedOpponents: CheckedOpponents;
  scores: ScoreMap;
}

export default function Scoreboard({ checkedOpponents, scores }: ScoreboardProps) {
  const visiblePlayers = currentPlayerDefs(checkedOpponents);

  return (
    <div className="scoreboard-panel">
      <div className="scoreboard-title">Scoreboard</div>
      <div className="scoreboard-row">
        {visiblePlayers.map((player, index) => (
          <Fragment key={player.id}>
            {index > 0 ? <div className="score-sep" /> : null}
            <div className={`score-chip ${player.id}`}>
              <span className="sc-name">{player.human ? "You" : player.name}</span>
              <span className="sc-num">{scores[player.id]}</span>
            </div>
          </Fragment>
        ))}
      </div>
    </div>
  );
}
