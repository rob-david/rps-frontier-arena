"use client";

import { useEffect, useRef, useState } from "react";

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
  type LastRoundChoices,
  OPPONENT_IDS,
  resolveRound,
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
let didNotifyAppOpened = false;

export default function Home() {
  const gameGenerationRef = useRef(0);
  const isResolvingRoundRef = useRef(false);
  const didNotifyFirstRoundPlayedRef = useRef(false);
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
  const [lastRoundChoices, setLastRoundChoices] = useState<LastRoundChoices | null>(null);
  const [history, setHistory] = useState<TournamentHistory[]>(() =>
    appendTournamentHeading([], 1),
  );

  useEffect(() => {
    window.getFullSessionHistoryText = () => getFullSessionHistoryText(history);
    return () => {
      delete window.getFullSessionHistoryText;
    };
  }, [history]);

  useEffect(() => {
    if (didNotifyAppOpened) {
      return;
    }
    didNotifyAppOpened = true;

    void fetch("/api/notify", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ event: "app_opened" }),
    }).catch(() => {
      // Notification is best-effort and must never impact gameplay UX.
    });
  }, []);

  const initTournament = (nextCheckedOpponents: CheckedOpponents) => {
    gameGenerationRef.current += 1;
    isResolvingRoundRef.current = false;
    setIsResolvingRound(false);

    const nextTournamentNum = tournamentNum + 1;
    setPlayers(createTournamentPlayers(nextCheckedOpponents));
    setRoundNum(0);
    setSelected(null);
    setGameOver(false);
    setChampion(null);
    setLastRoundChoices(null);
    setTournamentNum(nextTournamentNum);
    setHistory((prevHistory) => appendTournamentHeading(prevHistory, nextTournamentNum));
  };

  const handleToggleOpponent = (id: OpponentId) => {
    if (isResolvingRoundRef.current) {
      return;
    }

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
    if (isResolvingRoundRef.current) {
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

    if (!didNotifyFirstRoundPlayedRef.current) {
      didNotifyFirstRoundPlayedRef.current = true;
      void fetch("/api/notify", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ event: "first_round_played" }),
      }).catch(() => {
        // Notification is best-effort and must never impact gameplay UX.
      });
    }

    const requestGeneration = gameGenerationRef.current;
    isResolvingRoundRef.current = true;
    setIsResolvingRound(true);
    try {
      const choices: Record<string, Choice> = {};
      const historyText = getFullSessionHistoryText(history);
      const aiChoices = await fetchAIMoves(activePlayers, historyText);

      if (requestGeneration !== gameGenerationRef.current) {
        return;
      }

      activePlayers.forEach((player) => {
        if (player.human) {
          choices[player.id] = selected as Choice;
        } else {
          choices[player.id] = aiChoices[player.id as OpponentId];
        }
      });

      const nextRoundNum = roundNum + 1;
      const resolution = resolveRound(choices);
      setLastRoundChoices({
        roundNum: nextRoundNum,
        choices: { ...choices },
        eliminatedIds: resolution.tie ? [] : [...(resolution.eliminatedIds || [])],
      });

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
      if (requestGeneration === gameGenerationRef.current) {
        isResolvingRoundRef.current = false;
        setIsResolvingRound(false);
      }
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

      <OpponentsPanel
        checkedOpponents={checkedOpponents}
        isLocked={isResolvingRound}
        onToggleOpponent={handleToggleOpponent}
      />

      <div className="divider-rule" />

      <div className="table">
        <PlayersTable
          players={players}
          selected={selected}
          gameOver={gameOver}
          championId={champion?.id ?? null}
          lastRoundChoices={lastRoundChoices}
          isThinking={isResolvingRound}
          onSelectChoice={setSelected}
          onPlayRound={handlePlayRound}
        />
        <HistoryPanel history={history} />
      </div>

      <footer className="note">Powered by Claude &amp; GitHub Copilot · July 2026</footer>
    </div>
  );
}
