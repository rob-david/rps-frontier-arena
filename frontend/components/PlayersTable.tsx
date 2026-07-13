import { glyphs, labels, type Choice, type LastRoundChoices, type PlayerState } from "@/lib/game";

interface PlayersTableProps {
  players: PlayerState[];
  selected: Choice | null;
  isThinking: boolean;
  gameOver: boolean;
  championId: string | null;
  lastRoundChoices: LastRoundChoices | null;
  onSelectChoice: (choice: Choice) => void;
  onPlayRound: () => void;
}

function renderLiveCell(
  player: PlayerState,
  selected: Choice | null,
  isThinking: boolean,
  gameOver: boolean,
  championId: string | null,
  onSelectChoice: (choice: Choice) => void,
) {
  if (gameOver) {
    if (championId && player.id === championId) {
      return <div className="mini-badge champ">🏆</div>;
    }
    return <div className="mini-badge dash">—</div>;
  }

  if (!player.active) {
    return <div className="mini-badge dash">—</div>;
  }

  if (player.human) {
    return (
      <div className="mini-choices">
        {(["kamen", "nuzky", "papir"] as Choice[]).map((choice) => (
          <div
            key={choice}
            className={`choice-mini${selected === choice ? " selected" : ""}${isThinking ? " disabled" : ""}`}
            data-choice={choice}
            title={labels[choice]}
            onClick={() => {
              if (isThinking) {
                return;
              }
              onSelectChoice(choice);
            }}
          >
            {glyphs[choice]}
          </div>
        ))}
      </div>
    );
  }

  return <div className="mini-badge wait">?</div>;
}

function renderLastRoundCell(
  player: PlayerState,
  columnIndex: number,
  lastRoundChoices: LastRoundChoices | null,
) {
  const tag =
    columnIndex === 0 && lastRoundChoices ? <div className="round-tag">R{lastRoundChoices.roundNum}</div> : null;

  if (!lastRoundChoices) {
    return (
      <>
        {tag}
        <div className="mini-badge dash">—</div>
      </>
    );
  }

  const choice = lastRoundChoices.choices[player.id];
  if (!choice) {
    return (
      <>
        {tag}
        <div className="mini-badge dash">—</div>
      </>
    );
  }

  const wasEliminated = lastRoundChoices.eliminatedIds.includes(player.id);
  return (
    <>
      {tag}
      <div className={`mini-badge filled${wasEliminated ? " out-hit" : ""}`}>{glyphs[choice]}</div>
    </>
  );
}

export default function PlayersTable({
  players,
  selected,
  isThinking,
  gameOver,
  championId,
  lastRoundChoices,
  onSelectChoice,
  onPlayRound,
}: PlayersTableProps) {
  const userPlayer = players.find((player) => player.id === "user");
  const userActive = Boolean(userPlayer?.active);
  const playDisabled = gameOver ? false : isThinking || (userActive && !selected);

  return (
    <div className="game-column">
      <div className="players-grid" style={{ gridTemplateColumns: `repeat(${players.length}, 1fr)` }}>
        {players.map((player) => (
          <div key={`head-${player.id}`} className={`head-cell ${player.id}${!player.active ? " eliminated" : ""}`}>
            <div className="side-name">
              <span className="dot" />
              <span>{player.human ? "You" : player.name}</span>
              {!player.active ? <span className="x-mark">✖</span> : null}
            </div>
            {player.model ? (
              <div className="side-powered">
                {player.provider}
                <span className="model-name">{player.model}</span>
              </div>
            ) : null}
          </div>
        ))}

        {players.map((player) => (
          <div key={`live-${player.id}`} className="row-cell live-cell">
            {renderLiveCell(player, selected, isThinking, gameOver, championId, onSelectChoice)}
          </div>
        ))}

        {players.map((player, index) => (
          <div key={`last-round-${player.id}`} className="row-cell last-round-cell">
            {renderLastRoundCell(player, index, lastRoundChoices)}
          </div>
        ))}
      </div>

      <div className="cta-wrap">
        <button className={`cta${gameOver ? " champion-btn" : ""}`} onClick={onPlayRound} disabled={playDisabled}>
          {gameOver ? "New Tournament" : isThinking ? "Thinking..." : "Play Round"}
        </button>
      </div>
    </div>
  );
}
