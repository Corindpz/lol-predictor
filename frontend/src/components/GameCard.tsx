"use client";
import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { champIcon } from "@/lib/ddragon";

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
  const [imgError, setImgError] = useState(false);
  const kda = `${game.kills}/${game.deaths}/${game.assists}`;
  const resultColor = game.won ? "var(--blue)" : "var(--red)";
  const resultLabel = game.won ? "Victoire" : "Défaite";

  return (
    <button
      onClick={onClick}
      className="w-full text-left card-shine rounded-xl p-4 flex items-center gap-4 group transition-all hover:scale-[1.01]"
    >
      {/* Result bar */}
      <div className="w-1 self-stretch rounded-full shrink-0" style={{ background: resultColor }} />

      {/* Champion icon */}
      <div className="w-11 h-11 rounded-lg overflow-hidden shrink-0 relative"
        style={{ border: `1px solid var(--border)` }}>
        {!imgError ? (
          <img
            src={champIcon(game.champion)}
            alt={game.champion}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-sm font-bold"
            style={{ background: "var(--bg-hover)", color: "var(--gold)" }}>
            {game.champion.slice(0, 2)}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-bold text-sm" style={{ color: resultColor }}>{resultLabel}</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>·</span>
          <span className="text-xs font-medium">{game.champion}</span>
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-sm font-semibold font-mono">{kda}</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>{game.duration_min} min</span>
        </div>
      </div>

      <ChevronRight size={16} className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
        style={{ color: "var(--gold)" }} />
    </button>
  );
}
