interface GameCardProps {
  game: {
    match_id: string;
    champion: string;
    kills: number;
    deaths: number;
    assists: number;
    won: boolean;
    duration_min: number;
    player_team: string;
  };
  onClick: () => void;
}

export function GameCard({ game, onClick }: GameCardProps) {
  const kda = `${game.kills}/${game.deaths}/${game.assists}`;
  const teamColor = game.player_team === "blue" ? "var(--blue)" : "var(--red)";
  const resultColor = game.won ? "var(--blue)" : "var(--red)";
  const resultLabel = game.won ? "Victoire" : "Défaite";

  return (
    <button onClick={onClick} className="w-full text-left card-shine rounded-xl p-4 flex items-center gap-4 group transition-all">
      {/* Result bar */}
      <div className="w-1 self-stretch rounded-full shrink-0 transition-all"
        style={{ background: resultColor }} />

      {/* Champion */}
      <div className="w-10 h-10 rounded-lg flex items-center justify-center text-lg font-bold shrink-0"
        style={{ background: "var(--bg-hover)", border: "1px solid var(--border)" }}>
        {game.champion.slice(0, 2)}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sm" style={{ color: resultColor }}>{resultLabel}</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>·</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>{game.champion}</span>
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-sm font-semibold">{kda}</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>{game.duration_min} min</span>
          <span className="text-xs px-2 py-0.5 rounded-full"
            style={{ background: "var(--bg-hover)", color: teamColor, border: `1px solid ${teamColor}33` }}>
            Éq. {game.player_team === "blue" ? "Bleue" : "Rouge"}
          </span>
        </div>
      </div>

      {/* Arrow */}
      <span className="text-lg opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "var(--gold)" }}>→</span>
    </button>
  );
}
