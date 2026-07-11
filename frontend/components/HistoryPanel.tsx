import { labels, type TournamentHistory } from "@/lib/game";

interface HistoryPanelProps {
  history: TournamentHistory[];
}

export default function HistoryPanel({ history }: HistoryPanelProps) {
  const displayHistory = [...history].reverse();

  return (
    <div className="history-panel">
      <div className="history-title">Tournament History</div>
      <div className="history-feed">
        {displayHistory.map((group) => (
          <div key={group.heading}>
            <div className="tournament-heading">{group.heading}</div>
            {[...group.rounds].reverse().map((round) => (
              <div key={`${group.heading}-round-${round.roundNumber}`} className="round-block">
                <div className="round-title">Round {round.roundNumber}</div>
                {round.selections.map((selection, index) => (
                  <div key={`${selection.playerName}-${index}`} className="sel-line">
                    <span className="name">{selection.playerName}</span> selected {labels[selection.choice]}.
                  </div>
                ))}

                {round.tie ? <span className="tie-line">Tie — replay required.</span> : null}

                {!round.tie
                  ? round.eliminatedNames.map((name) => (
                      <span key={`${group.heading}-${round.roundNumber}-${name}`} className="elim-line">
                        {name} was eliminated.
                      </span>
                    ))
                  : null}

                {!round.tie && round.championName ? (
                  <span className="champ-line">Champion: {round.championName} 🏆</span>
                ) : null}

                {!round.tie && !round.championName ? (
                  <span className="remain-line">{round.remainingCount} players remain.</span>
                ) : null}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
