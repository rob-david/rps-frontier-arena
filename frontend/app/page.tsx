"use client";

import { useEffect, useState } from "react";

import HistoryPanel from "@/components/HistoryPanel";
import OpponentsPanel from "@/components/OpponentsPanel";
import PlayersTable from "@/components/PlayersTable";
import Scoreboard from "@/components/Scoreboard";
import {
  appendRound,
  appendTournamentHeading,
  applyRound,
  createInitialScores,
  createTournamentPlayers,
  DEFAULT_CHECKED_OPPONENTS,
  fetchAIMoves,
  getFullSessionHistoryText,
  OPPONENT_IDS,
  type CheckedOpponents,
  type Choice,
  type OpponentId,
  type PlayerState,
  type TournamentHistory,
} from "@/lib/game";

declare global {
  interface Window {
    getFullSessionHistoryText?: () => string;
  }
}

const INITIAL_CHECKED_OPPONENTS: CheckedOpponents = {
  ...DEFAULT_CHECKED_OPPONENTS,
};

export default function Home() {
  const [checkedOpponents, setCheckedOpponents] =
    useState<CheckedOpponents>(INITIAL_CHECKED_OPPONENTS);
  const [players, setPlayers] = useState<PlayerState[]>(() =>
    createTournamentPlayers(INITIAL_CHECKED_OPPONENTS),
  );
  const [tournamentNum, setTournamentNum] = useState(1);
  const [roundNum, setRoundNum] = useState(0);
  const [selected, setSelected] = useState<Choice | null>(null);
  const [isResolvingRound, setIsResolvingRound] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [champion, setChampion] = useState<PlayerState | null>(null);
  const [scores, setScores] = useState(createInitialScores);
  const [history, setHistory] = useState<TournamentHistory[]>(() =>
    appendTournamentHeading([], 1),
  );

  useEffect(() => {
    window.getFullSessionHistoryText = () => getFullSessionHistoryText(history);
    return () => {
      delete window.getFullSessionHistoryText;
    };
  }, [history]);

  const initTournament = (nextCheckedOpponents: CheckedOpponents) => {
    const nextTournamentNum = tournamentNum + 1;
    setPlayers(createTournamentPlayers(nextCheckedOpponents));
    setRoundNum(0);
    setSelected(null);
    setGameOver(false);
    setChampion(null);
    setTournamentNum(nextTournamentNum);
    setHistory((prevHistory) => appendTournamentHeading(prevHistory, nextTournamentNum));
  };

  const handleToggleOpponent = (id: OpponentId) => {
    const activeCount = OPPONENT_IDS.filter((opponentId) => checkedOpponents[opponentId]).length;
    if (checkedOpponents[id] && activeCount <= 1) {
      return;
    }

    const nextCheckedOpponents = {
      ...checkedOpponents,
      [id]: !checkedOpponents[id],
    };

    setCheckedOpponents(nextCheckedOpponents);
    initTournament(nextCheckedOpponents);
  };

  const handlePlayRound = async () => {
    if (isResolvingRound) {
      return;
    }

    if (gameOver) {
      initTournament(checkedOpponents);
      return;
    }

    const activePlayers = players.filter((player) => player.active);
    const userPlayer = activePlayers.find((player) => player.id === "user");
    if (userPlayer && !selected) {
      return;
    }

    setIsResolvingRound(true);
    try {
      const choices: Record<string, Choice> = {};
      const historyText = getFullSessionHistoryText(history);
      const aiChoices = await fetchAIMoves(activePlayers, historyText);

      activePlayers.forEach((player) => {
        if (player.human) {
          choices[player.id] = selected as Choice;
        } else {
          choices[player.id] = aiChoices[player.id as OpponentId];
        }
      });

      const nextRoundNum = roundNum + 1;
      const output = applyRound({
        players,
        scores,
        choices,
        roundNumber: nextRoundNum,
      });

      setRoundNum(nextRoundNum);
      setPlayers(output.players);
      setScores(output.scores);
      setHistory((prevHistory) => appendRound(prevHistory, output.roundRecord));
      setGameOver(output.gameOver);
      setChampion(output.champion);
      setSelected(null);
    } finally {
      setIsResolvingRound(false);
    }
  };

  const activeCount = players.filter((player) => player.active).length;
  const userActive = Boolean(players.find((player) => player.id === "user")?.active);
  const hint = userActive
    ? "Pick a symbol and play the round"
    : "You are eliminated — AI keep playing";

  return (
    <div className="app">
      <header>
        <div className="eyebrow">Frontier Arena · 1 player, 4 AI</div>
        <h1>
          Rock, Paper, <span className="accent">Scissors</span>
        </h1>
        <div className="status-bar">
          {gameOver ? (
            <>
              Tournament #{tournamentNum} · <span className="champ-tag">🏆 Champion: {champion?.name}</span>
            </>
          ) : (
            <>
              Tournament #{tournamentNum} · Round {roundNum + 1} · <b>{activeCount} players remain</b> · {hint}
            </>
          )}
        </div>
      </header>

      <Scoreboard checkedOpponents={checkedOpponents} scores={scores} />

      <div className="divider-rule" />

      <OpponentsPanel checkedOpponents={checkedOpponents} onToggleOpponent={handleToggleOpponent} />

      <div className="divider-rule" />

      <div className="table">
        <PlayersTable
          players={players}
          selected={selected}
          isResolvingRound={isResolvingRound}
          gameOver={gameOver}
          championId={champion?.id ?? null}
          onSelectChoice={setSelected}
          onPlayRound={handlePlayRound}
        />
        <HistoryPanel history={history} />
      </div>

      <footer className="note">Powered by Claude &amp; GitHub Copilot · July 2026</footer>
    </div>
  );
}
