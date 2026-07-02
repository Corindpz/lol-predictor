"use client";
import { useState } from "react";
import { ChevronRight } from "lucide-react";
import { champIcon } from "@/lib/ddragon";

export interface Game {
  match_id: string;
  champion: string;
  kills: number;
  deaths: number;
  assists: number;
  won: boolean;
  duration_min: number;
  player_team: string;
  damage?: number;
}

interface GameCardProps {
  game: Game;
  onClick: () => void;
}

function formatK(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`;
}

export function GameCard({ game, onClick }: GameCardProps) {
  const [imgError, setImgError] = useState(false);
  const kda = `${game.kills}/${game.deaths}/${game.assists}`;
  const resultColor = game.won ? "var(--blue)" : "var(--red)";
  const resultLabel = game.won ? "Victoire" : "Défaite";

  return (
    <button
      onClick={onClick}
      className="w-full text-left card-shine rounded-xl p-5 flex items-center gap-5 group transition-all hover:scale-[1.005]"
    >
      {/* Result bar */}
      <div className="w-1.5 self-stretch rounded-full shrink-0" style={{ background: resultColor }} />

      {/* Champion icon */}
      <div className="w-14 h-14 rounded-lg overflow-hidden shrink-0 relative"
        style={{ border: `1px solid var(--border)` }}>
        {!imgError ? (
          <img
            src={champIcon(game.champion)}
            alt={game.champion}
            className="w-full h-full object-cover"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-base font-bold"
            style={{ background: "var(--bg-hover)", color: "var(--gold)" }}>
            {game.champion.slice(0, 2)}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2.5">
          <span className="font-bold text-base" style={{ color: resultColor }}>{resultLabel}</span>
          <span className="text-sm" style={{ color: "var(--muted)" }}>·</span>
          <span className="text-sm font-medium">{game.champion}</span>
        </div>
        <div className="flex items-center gap-4 mt-1">
          <span className="text-base font-semibold font-mono">{kda}</span>
          <span className="text-sm" style={{ color: "var(--muted)" }}>{game.duration_min} min</span>
        </div>
      </div>

      {/* Dégâts */}
      {game.damage !== undefined && (
        <div className="text-right shrink-0">
          <p className="text-xs mb-0.5" style={{ color: "var(--muted)" }}>Dégâts</p>
          <p className="text-base font-bold tabular-nums" style={{ color: "var(--gold)" }}>
            {formatK(game.damage)}
          </p>
        </div>
      )}

      <ChevronRight size={18} className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
        style={{ color: "var(--gold)" }} />
    </button>
  );
}
