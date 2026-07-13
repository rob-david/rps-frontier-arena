export type Choice = "kamen" | "nuzky" | "papir";
export type PlayerId = "user" | "sam" | "claude" | "elon" | "sergey";
export type OpponentId = Exclude<PlayerId, "user">;

export interface PlayerDefinition {
  id: PlayerId;
  name: string;
  provider: string | null;
  model: string | null;
  human?: boolean;
}

export interface PlayerState extends PlayerDefinition {
  active: boolean;
}

export type CheckedOpponents = Record<OpponentId, boolean>;
export type ScoreMap = Record<PlayerId, number>;

export interface RoundSelection {
  playerName: string;
  choice: Choice;
}

export interface RoundRecord {
  roundNumber: number;
  selections: RoundSelection[];
  tie: boolean;
  eliminatedNames: string[];
  remainingCount: number;
  championName: string | null;
}

export interface TournamentHistory {
  heading: string;
  rounds: RoundRecord[];
}

export interface RoundResolution {
  tie: boolean;
  eliminatedIds?: PlayerId[];
}

export interface LastRoundChoices {
  roundNum: number;
  choices: Partial<Record<PlayerId, Choice>>;
  eliminatedIds: PlayerId[];
}

export interface RoundApplyInput {
  players: PlayerState[];
  scores: ScoreMap;
  choices: Record<string, Choice>;
  roundNumber: number;
}

export interface RoundApplyOutput {
  players: PlayerState[];
  scores: ScoreMap;
  roundRecord: RoundRecord;
  gameOver: boolean;
  champion: PlayerState | null;
}

interface AIMoveResponse {
  choice: string;
}

export const glyphs: Record<Choice, string> = {
  kamen: "🪨",
  nuzky: "✂️",
  papir: "📄",
};

export const labels: Record<Choice, string> = {
  kamen: "Rock",
  nuzky: "Scissors",
  papir: "Paper",
};

export const PLAYER_DEFS: PlayerDefinition[] = [
  { id: "user", name: "You", provider: null, model: null, human: true },
  { id: "sam", name: "Sam", provider: "OpenAI", model: "GPT-5.4" },
  { id: "claude", name: "Claude", provider: "Anthropic", model: "Claude Sonnet 5" },
  { id: "elon", name: "Elon", provider: "xAI", model: "Grok 4.3" },
  { id: "sergey", name: "Sergey", provider: "Google", model: "Gemini 3.1 Pro" },
];

export const OPPONENT_IDS: OpponentId[] = ["sam", "claude", "elon", "sergey"];

export const DEFAULT_CHECKED_OPPONENTS: CheckedOpponents = {
  sam: true,
  claude: true,
  elon: true,
  sergey: true,
};

export function createInitialScores(): ScoreMap {
  return { user: 0, sam: 0, claude: 0, elon: 0, sergey: 0 };
}

export function currentPlayerDefs(checkedOpponents: CheckedOpponents): PlayerDefinition[] {
  return PLAYER_DEFS.filter((player) => player.human || checkedOpponents[player.id as OpponentId]);
}

export function createTournamentPlayers(checkedOpponents: CheckedOpponents): PlayerState[] {
  return currentPlayerDefs(checkedOpponents).map((player) => ({ ...player, active: true }));
}

export function beats(a: Choice, b: Choice): boolean {
  return (
    (a === "kamen" && b === "nuzky") ||
    (a === "nuzky" && b === "papir") ||
    (a === "papir" && b === "kamen")
  );
}

export function resolveRound(choices: Record<string, Choice>): RoundResolution {
  const types = Object.values(choices);
  const unique = [...new Set(types)];

  if (unique.length === 1) {
    return { tie: true };
  }

  if (unique.length === 2) {
    const [a, b] = unique;
    const winnerType = beats(a, b) ? a : b;
    const eliminatedIds = Object.keys(choices).filter((id) => choices[id] !== winnerType) as PlayerId[];
    return { tie: false, eliminatedIds };
  }

  const counts: Record<string, number> = {};
  types.forEach((type) => {
    counts[type] = (counts[type] || 0) + 1;
  });

  const maxCount = Math.max(...Object.values(counts));
  const top = Object.keys(counts).filter((type) => counts[type] === maxCount);
  if (top.length !== 1) {
    return { tie: true };
  }

  const majority = top[0] as Choice;
  const eliminatedIds = Object.keys(choices).filter((id) => choices[id] !== majority) as PlayerId[];
  return { tie: false, eliminatedIds };
}

export function pickRandomChoice(randomFn: () => number = Math.random): Choice {
  const options: Choice[] = ["kamen", "nuzky", "papir"];
  return options[Math.floor(randomFn() * 3)];
}

function isChoice(value: string): value is Choice {
  return value === "kamen" || value === "nuzky" || value === "papir";
}

export async function fetchAIMoves(
  activePlayers: PlayerState[],
  historyText: string,
): Promise<Record<OpponentId, Choice>> {
  const aiPlayers = activePlayers.filter((player) => !player.human) as Array<
    PlayerState & { id: OpponentId }
  >;
  const activePlayerIds = activePlayers.map((player) => player.id);

  const pairs = await Promise.all(
    aiPlayers.map(async (player) => {
      try {
        const response = await fetch("/api/ai-move", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            player_id: player.id,
            active_players: activePlayerIds,
            history: historyText,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = (await response.json()) as AIMoveResponse;
        if (!isChoice(data.choice)) {
          throw new Error("Invalid choice payload");
        }

        return [player.id, data.choice] as const;
      } catch {
        return [player.id, pickRandomChoice()] as const;
      }
    }),
  );

  return Object.fromEntries(pairs) as Record<OpponentId, Choice>;
}

export function applyRound(input: RoundApplyInput): RoundApplyOutput {
  const nextPlayers = input.players.map((player) => ({ ...player }));
  const nextScores: ScoreMap = { ...input.scores };

  const activePlayers = nextPlayers.filter((player) => player.active);
  const resolution = resolveRound(input.choices);
  const selections: RoundSelection[] = activePlayers.map((player) => ({
    playerName: player.name,
    choice: input.choices[player.id],
  }));

  if (resolution.tie) {
    activePlayers.forEach((player) => {
      nextScores[player.id] += 1;
    });

    return {
      players: nextPlayers,
      scores: nextScores,
      roundRecord: {
        roundNumber: input.roundNumber,
        selections,
        tie: true,
        eliminatedNames: [],
        remainingCount: activePlayers.length,
        championName: null,
      },
      gameOver: false,
      champion: null,
    };
  }

  const eliminatedNames: string[] = [];
  (resolution.eliminatedIds || []).forEach((id) => {
    const player = nextPlayers.find((candidate) => candidate.id === id);
    if (!player) {
      return;
    }
    player.active = false;
    eliminatedNames.push(player.name);
  });

  const remainingPlayers = nextPlayers.filter((player) => player.active);
  remainingPlayers.forEach((player) => {
    nextScores[player.id] += 1;
  });

  let champion: PlayerState | null = null;
  if (remainingPlayers.length === 1) {
    champion = remainingPlayers[0];
    nextScores[champion.id] += 2;
  }

  return {
    players: nextPlayers,
    scores: nextScores,
    roundRecord: {
      roundNumber: input.roundNumber,
      selections,
      tie: false,
      eliminatedNames,
      remainingCount: remainingPlayers.length,
      championName: champion ? champion.name : null,
    },
    gameOver: Boolean(champion),
    champion,
  };
}

export function appendTournamentHeading(history: TournamentHistory[], tournamentNumber: number): TournamentHistory[] {
  return [...history, { heading: `Tournament #${tournamentNumber}`, rounds: [] }];
}

export function appendRound(history: TournamentHistory[], roundRecord: RoundRecord): TournamentHistory[] {
  if (history.length === 0) {
    return history;
  }

  const nextHistory = history.map((group) => ({ ...group, rounds: [...group.rounds] }));
  const current = nextHistory[nextHistory.length - 1];
  current.rounds.push(roundRecord);
  return nextHistory;
}

function roundRecordToText(round: RoundRecord): string {
  const lines: string[] = [`Round ${round.roundNumber}`];

  round.selections.forEach((selection) => {
    lines.push(`${selection.playerName} selected ${labels[selection.choice]}.`);
  });

  if (round.tie) {
    lines.push("Tie — replay required.");
  } else {
    round.eliminatedNames.forEach((name) => {
      lines.push(`${name} was eliminated.`);
    });

    if (round.championName) {
      lines.push(`Champion: ${round.championName} 🏆`);
    } else {
      lines.push(`${round.remainingCount} players remain.`);
    }
  }

  return lines.join("\n");
}

export function getFullSessionHistoryText(history: TournamentHistory[]): string {
  return history
    .map((group) => [group.heading, ...group.rounds.map((round) => roundRecordToText(round))].join("\n\n"))
    .join("\n\n");
}
