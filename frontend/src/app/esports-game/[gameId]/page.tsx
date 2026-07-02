"use client";
import { use, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft, Loader2, Trophy, Skull, TrendingUp, AlertCircle,
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface CurvePoint { minute: number; blue_win_prob: number; gold_diff: number; kills_diff: number; }
interface BlamePlayer {
  pid: number; name: string; champion: string; team: string; won: boolean;
  kda_str: string; kill_participation: number; cs: number; gold: number; impact_score: number;
}
interface EsportsGame {
  esports_game_id: string; blue_won: boolean; duration_min: number;
  curve: CurvePoint[]; blame: BlamePlayer[]; note: string;
}

function WinCurve({ curve, blueWon }: { curve: CurvePoint[]; blueWon: boolean }) {
  const lineColor = blueWon ? "#0bc4e3" : "#e84057";

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const p = payload[0].value as number;
    const gd = payload[1]?.value as number;
    return (
      <div className="card-shine rounded-lg p-3 text-xs space-y-1.5" style={{ minWidth: 150 }}>
        <p style={{ color: "var(--muted)" }}>{label} min</p>
        <p className="font-bold text-sm" style={{ color: p > 50 ? "#0bc4e3" : "#e84057" }}>
          Bleue : {p.toFixed(1)}% win
        </p>
        {gd !== undefined && (
          <p style={{ color: gd >= 0 ? "#0bc4e3" : "#e84057" }}>
            {gd >= 0 ? "+" : ""}{gd.toLocaleString()}g diff
          </p>
        )}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={280}>
      <AreaChart data={curve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={lineColor} stopOpacity={0.25} />
            <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
        <XAxis dataKey="minute" tick={{ fill: "rgba(232,224,208,0.4)", fontSize: 11 }}
          tickFormatter={v => `${v}m`} />
        <YAxis domain={[0, 100]} tick={{ fill: "rgba(232,224,208,0.4)", fontSize: 11 }}
          tickFormatter={v => `${v}%`} />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={50} stroke="rgba(255,255,255,0.15)" strokeDasharray="4 4" />
        <Area type="monotone" dataKey="blue_win_prob"
          stroke={lineColor} strokeWidth={2.5} fill="url(#grad)" dot={false} />
        <Area type="monotone" dataKey="gold_diff" hide />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function BlameRow({ player, rank }: { player: BlamePlayer; rank: number }) {
  const isCarry = player.impact_score > 15;
  const isFautif = player.impact_score < -5;
  const accent = isCarry ? "var(--blue)" : isFautif ? "var(--red)" : "var(--muted)";
  const maxImpact = 80;
  const barW = Math.min(Math.abs(player.impact_score) / maxImpact * 100, 100);
  const badge = rank === 1 ? (player.won ? "MVP" : "Fautif #1") : null;
  const badgeColor = player.won ? "var(--gold)" : "var(--red)";

  return (
    <div className="flex items-center gap-3 py-2.5 px-2 rounded-lg"
      style={{ borderBottom: "1px solid var(--border)" }}>
      <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold shrink-0"
        style={{ background: "var(--bg-hover)", color: "var(--gold)" }}>
        {player.champion.slice(0, 2)}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="font-bold text-sm truncate">{player.champion}</span>
          {badge && (
            <span className="text-xs px-1.5 py-0.5 rounded font-bold shrink-0"
              style={{ background: `${badgeColor}20`, color: badgeColor, fontSize: 10 }}>
              {badge}
            </span>
          )}
        </div>
        <span className="text-xs truncate block" style={{ color: "var(--muted)" }}>{player.name}</span>
        <div className="flex items-center gap-2 mt-1.5">
          <div className="flex-1 h-1 rounded-full" style={{ background: "var(--bg)" }}>
            <div className="h-full rounded-full" style={{ width: `${barW}%`, background: accent }} />
          </div>
          <span className="text-xs font-mono font-bold shrink-0 w-10 text-right" style={{ color: accent }}>
            {player.impact_score > 0 ? "+" : ""}{player.impact_score}
          </span>
        </div>
      </div>
      <div className="text-right shrink-0">
        <p className="font-mono text-xs font-semibold">{player.kda_str}</p>
        <p className="text-xs" style={{ color: "var(--muted)" }}>
          {player.cs} CS · {Math.round(player.gold / 1000)}k
        </p>
      </div>
    </div>
  );
}

export default function EsportsGamePage({ params }: { params: Promise<{ gameId: string }> }) {
  const { gameId } = use(params);
  const searchParams = useSearchParams();
  const router = useRouter();
  const team1 = searchParams.get("t1") ?? "Bleu";
  const team2 = searchParams.get("t2") ?? "Rouge";

  const [data, setData] = useState<EsportsGame | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API}/pro/esports-game/${gameId}`)
      .then(r => r.json())
      .then(d => {
        if (d.detail) setError(d.detail);
        else setData(d);
      })
      .catch(() => setError("Erreur de connexion"))
      .finally(() => setLoading(false));
  }, [gameId]);

  if (loading) return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-3" style={{ color: "var(--muted)" }}>
      <Loader2 size={20} className="animate-spin" style={{ color: "var(--gold)" }} />
      <p className="text-sm">Analyse en cours — récupération live stats lolesports...</p>
      <p className="text-xs opacity-50">Environ 30 secondes</p>
    </main>
  );

  if (error || !data) return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-4" style={{ color: "var(--red)" }}>
      <AlertCircle size={32} />
      <p>{error || "Game introuvable"}</p>
      <button onClick={() => router.back()} className="text-sm opacity-50 hover:opacity-100" style={{ color: "var(--gold)" }}>
        Retour
      </button>
    </main>
  );

  const blueTeam = data.blame.filter(p => p.team === "blue");
  const redTeam  = data.blame.filter(p => p.team === "red");

  const sortTeam = (players: BlamePlayer[], won: boolean) =>
    [...players].sort((a, b) => won ? b.impact_score - a.impact_score : a.impact_score - b.impact_score);

  const blueWon = data.blue_won;
  const sortedBlue = sortTeam(blueTeam, blueWon);
  const sortedRed  = sortTeam(redTeam, !blueWon);

  // Moment pivot : première fois que l'équipe gagnante dépasse 65%
  const winnerLabel = blueWon ? team1 : team2;
  const pivot = data.curve.find(c => blueWon ? c.blue_win_prob > 65 : c.blue_win_prob < 35);

  return (
    <main className="min-h-screen px-6 md:px-12 lg:px-20 py-12">
      <button onClick={() => router.back()}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      {/* Header */}
      <div className="mb-8">
        <p className="text-xs tracking-widest uppercase mb-2" style={{ color: "var(--gold-dim)" }}>
          Analyse game de tournoi · {data.duration_min} min
        </p>
        <div className="flex items-center gap-6">
          <h1 className="text-4xl font-black text-gold-gradient">
            {team1} <span className="text-2xl opacity-40">vs</span> {team2}
          </h1>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg"
            style={{ background: blueWon ? "rgba(11,196,227,0.1)" : "rgba(232,84,87,0.1)",
              border: `1px solid ${blueWon ? "var(--blue)" : "var(--red)"}` }}>
            <Trophy size={14} style={{ color: blueWon ? "var(--blue)" : "var(--red)" }} />
            <span className="font-bold text-sm" style={{ color: blueWon ? "var(--blue)" : "var(--red)" }}>
              {winnerLabel} gagne
            </span>
          </div>
        </div>
        {pivot && (
          <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>
            Game basculée à la minute {pivot.minute} — {winnerLabel} prend le contrôle
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Courbe + note */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card-shine rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={13} style={{ color: "var(--gold)" }} />
              <p className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--gold-dim)" }}>
                Win % équipe bleue ({team1})
              </p>
            </div>
            <WinCurve curve={data.curve} blueWon={blueWon} />
          </div>

          {/* Note données partielles */}
          <div className="card-shine rounded-xl p-4 flex items-start gap-3">
            <AlertCircle size={14} className="shrink-0 mt-0.5" style={{ color: "var(--gold-dim)" }} />
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              {data.note} — features disponibles : gold, kills, tours, dragons, barons, CS, niveaux.
              Wards, dégâts et XP non disponibles via lolesports API.
            </p>
          </div>
        </div>

        {/* Blame */}
        <div className="space-y-4">
          {/* Équipe bleue */}
          <div className="card-shine rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full" style={{ background: "var(--blue)" }} />
              <p className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--muted)" }}>
                {team1} {blueWon ? <Trophy size={11} style={{ display: "inline" }} /> : ""}
              </p>
            </div>
            {sortedBlue.map((p, i) => (
              <BlameRow key={p.pid} player={p} rank={i + 1} />
            ))}
          </div>

          {/* Équipe rouge */}
          <div className="card-shine rounded-xl p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full" style={{ background: "var(--red)" }} />
              <p className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--muted)" }}>
                {team2} {!blueWon ? <Trophy size={11} style={{ display: "inline" }} /> : ""}
              </p>
            </div>
            {sortedRed.map((p, i) => (
              <BlameRow key={p.pid} player={p} rank={i + 1} />
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
