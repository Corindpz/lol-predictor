"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { GameCard } from "@/components/GameCard";

const API = "http://localhost:8000";

interface Game {
  match_id: string; champion: string; kills: number; deaths: number;
  assists: number; won: boolean; duration_min: number; player_team: string;
}

export default function PlayerPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = use(params);
  const router = useRouter();
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const riotId = decodeURIComponent(slug).replace("-", "#");

  useEffect(() => {
    fetch(`${API}/player/${slug}`)
      .then(r => r.ok ? r.json() : r.json().then(e => Promise.reject(e.detail)))
      .then(d => setGames(d.games))
      .catch(e => setError(typeof e === "string" ? e : "Erreur de chargement"))
      .finally(() => setLoading(false));
  }, [slug]);

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
        {!loading && !error && (
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>{games.length} parties analysées</p>
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
