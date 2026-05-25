"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { GameCard } from "@/components/GameCard";
import { initDDragon } from "@/lib/ddragon";

const API = "http://localhost:8000";

interface Game {
  match_id: string; champion: string; kills: number; deaths: number;
  assists: number; won: boolean; duration_min: number; player_team: string;
}

// Cache session en mémoire (survit aux navigations back/forward sans re-fetch)
const _cache: Record<string, Game[]> = {};

export default function PlayerPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const router = useRouter();
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(!_cache[slug]);
  const [error, setError] = useState("");
  const riotId = decodeURIComponent(slug).replace("-", "#");

  useEffect(() => {
    initDDragon();

    if (_cache[slug]) {
      setGames(_cache[slug]);
      return;
    }

    fetch(`${API}/player/${slug}`)
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail)))
      .then(d => {
        _cache[slug] = d.games;
        setGames(d.games);
      })
      .catch(e => setError(typeof e === "string" ? e : "Erreur de chargement"))
      .finally(() => setLoading(false));
  }, [slug]);

  const wins = games.filter(g => g.won).length;
  const losses = games.length - wins;

  return (
    <main className="min-h-screen px-4 py-10 max-w-xl mx-auto">
      <button onClick={() => router.push("/")}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      <div className="mb-8">
        <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>Joueur</p>
        <h1 className="text-4xl font-black text-gold-gradient">{riotId}</h1>
        {!loading && !error && games.length > 0 && (
          <div className="flex items-center gap-3 mt-2">
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              {games.length} parties récentes
            </span>
            <span className="text-sm font-semibold" style={{ color: "var(--blue)" }}>{wins}V</span>
            <span className="text-sm font-semibold" style={{ color: "var(--red)" }}>{losses}D</span>
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              — {Math.round(wins / games.length * 100)}% WR
            </span>
          </div>
        )}
      </div>

      {loading && (
        <div className="flex items-center gap-3 py-20 justify-center" style={{ color: "var(--muted)" }}>
          <Loader2 size={20} className="animate-spin" style={{ color: "var(--gold)" }} />
          Chargement des parties...
        </div>
      )}

      {error && (
        <div className="card-shine rounded-xl p-6 text-center" style={{ color: "var(--red)" }}>
          {error}
        </div>
      )}

      <div className="space-y-2">
        {games.map(g => (
          <GameCard
            key={g.match_id}
            game={g}
            onClick={() => router.push(`/game/${g.match_id}?team=${g.player_team}`)}
          />
        ))}
      </div>
    </main>
  );
}
