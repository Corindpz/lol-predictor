"use client";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, TrendingDown, TrendingUp, Minus, AlertTriangle, Flame } from "lucide-react";
import { GameCard, type Game } from "@/components/GameCard";
import { initDDragon } from "@/lib/ddragon";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface TiltData {
  streak: { type: "win" | "loss"; count: number };
  recentKda: number;
  prevKda: number;
  kdaDelta: number;
  isTilting: boolean;
  isStreaking: boolean;
}

function kda(g: Game) { return (g.kills + g.assists) / Math.max(g.deaths, 1); }

function computeTilt(games: Game[]): TiltData | null {
  if (games.length < 2) return null;

  // Streak depuis la game la plus récente
  const streakType = games[0].won ? "win" : "loss";
  let streakCount = 0;
  for (const g of games) {
    if (g.won !== (streakType === "win")) break;
    streakCount++;
  }

  // KDA : 5 dernières vs 5 précédentes
  const recent = games.slice(0, Math.min(5, games.length));
  const prev   = games.slice(5, Math.min(10, games.length));
  const recentKda = recent.reduce((s, g) => s + kda(g), 0) / recent.length;
  const prevKda   = prev.length ? prev.reduce((s, g) => s + kda(g), 0) / prev.length : recentKda;
  const kdaDelta  = recentKda - prevKda;

  return {
    streak: { type: streakType, count: streakCount },
    recentKda,
    prevKda,
    kdaDelta,
    isTilting:   streakType === "loss" && streakCount >= 3 && kdaDelta < -0.3,
    isStreaking:  streakType === "win"  && streakCount >= 3,
  };
}

function TiltTracker({ games }: { games: Game[] }) {
  const data = computeTilt(games);
  if (!data) return null;

  const { streak, recentKda, kdaDelta, isTilting, isStreaking } = data;

  const streakColor = streak.type === "win" ? "var(--blue)" : "var(--red)";
  const streakBg    = streak.type === "win" ? "rgba(11,196,227,0.08)" : "rgba(232,64,87,0.08)";
  const streakBorder= streak.type === "win" ? "rgba(11,196,227,0.25)" : "rgba(232,64,87,0.25)";

  const KdaIcon = kdaDelta > 0.2 ? TrendingUp : kdaDelta < -0.2 ? TrendingDown : Minus;
  const kdaColor = kdaDelta > 0.2 ? "var(--blue)" : kdaDelta < -0.2 ? "var(--red)" : "var(--muted)";

  return (
    <div className="mb-8 space-y-3">
      {/* Alerte tilt */}
      {isTilting && (
        <div className="rounded-xl px-4 py-3 flex items-center gap-3"
          style={{ background: "rgba(232,64,87,0.12)", border: "1px solid rgba(232,64,87,0.4)" }}>
          <AlertTriangle size={15} style={{ color: "var(--red)", flexShrink: 0 }} />
          <div>
            <p className="text-sm font-bold" style={{ color: "var(--red)" }}>
              Tilt détecté — {streak.count} défaites consécutives
            </p>
            <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
              KDA en chute ({recentKda.toFixed(2)} vs {data.prevKda.toFixed(2)} sur les 5 précédentes). Peut-être une pause ?
            </p>
          </div>
        </div>
      )}

      {/* Alerte streak win */}
      {isStreaking && (
        <div className="rounded-xl px-4 py-3 flex items-center gap-3"
          style={{ background: "rgba(11,196,227,0.08)", border: "1px solid rgba(11,196,227,0.25)" }}>
          <Flame size={15} style={{ color: "var(--blue)", flexShrink: 0 }} />
          <p className="text-sm font-bold" style={{ color: "var(--blue)" }}>
            {streak.count} victoires d&apos;affilée — keep going
          </p>
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        {/* Streak */}
        <div className="card-shine rounded-xl p-5 text-center"
          style={{ border: `1px solid ${streakBorder}`, background: streakBg }}>
          <p className="text-sm mb-1.5" style={{ color: "var(--muted)" }}>Streak</p>
          <p className="text-3xl font-black" style={{ color: streakColor }}>
            {streak.count}{streak.type === "win" ? "V" : "D"}
          </p>
          <p className="text-sm mt-1" style={{ color: streakColor }}>consécutives</p>
        </div>

        {/* KDA récent */}
        <div className="card-shine rounded-xl p-5 text-center">
          <p className="text-sm mb-1.5" style={{ color: "var(--muted)" }}>KDA (5 dern.)</p>
          <p className="text-3xl font-black" style={{ color: "var(--gold)" }}>
            {recentKda.toFixed(2)}
          </p>
          <div className="flex items-center justify-center gap-1 mt-1">
            <KdaIcon size={13} style={{ color: kdaColor }} />
            <p className="text-sm" style={{ color: kdaColor }}>
              {kdaDelta >= 0 ? "+" : ""}{kdaDelta.toFixed(2)}
            </p>
          </div>
        </div>

        {/* Indicateur forme */}
        <div className="card-shine rounded-xl p-5 text-center">
          <p className="text-sm mb-1.5" style={{ color: "var(--muted)" }}>Forme</p>
          {isTilting ? (
            <>
              <p className="text-3xl font-black" style={{ color: "var(--red)" }}>Tilt</p>
              <p className="text-sm mt-1" style={{ color: "var(--red)" }}>Break conseillé</p>
            </>
          ) : isStreaking ? (
            <>
              <p className="text-3xl font-black" style={{ color: "var(--blue)" }}>Hot</p>
              <p className="text-sm mt-1" style={{ color: "var(--blue)" }}>Profites-en</p>
            </>
          ) : (
            <>
              <p className="text-3xl font-black" style={{ color: "var(--muted)" }}>Ok</p>
              <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>Neutre</p>
            </>
          )}
        </div>
      </div>
    </div>
  );
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
    <main className="min-h-screen px-6 md:px-12 lg:px-20 py-12">
      <button onClick={() => router.push("/")}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      <div className="mb-8">
        <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>Joueur</p>
        <h1 className="text-5xl font-black text-gold-gradient">{riotId}</h1>
        {!loading && !error && games.length > 0 && (
          <div className="flex items-center gap-3 mt-3">
            <span className="text-base" style={{ color: "var(--muted)" }}>
              {games.length} parties récentes
            </span>
            <span className="text-base font-semibold" style={{ color: "var(--blue)" }}>{wins}V</span>
            <span className="text-base font-semibold" style={{ color: "var(--red)" }}>{losses}D</span>
            <span className="text-base" style={{ color: "var(--muted)" }}>
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

      {!loading && !error && games.length > 0 && <TiltTracker games={games} />}

      <div className="space-y-3">
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
