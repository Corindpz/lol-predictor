"use client";
import { use, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2, Trophy, Skull, TrendingUp, Swords, Users } from "lucide-react";
import { champIcon, initDDragon } from "@/lib/ddragon";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";

const API = "http://localhost:8000";

interface CurvePoint { minute: number; player_win_prob: number; gold_diff: number; kills_diff: number; }
interface BlamePlayer {
  pid: number; name: string; champion: string; team: string; won: boolean;
  kda_str: string; kill_participation: number; wards_placed: number;
  wards_killed: number; cs: number; gold: number; impact_score: number;
}
interface GameData {
  match_id: string; blue_won: boolean; duration_min: number;
  curve: CurvePoint[]; key_events: Array<{min: number; label: string; team: string}>;
  blame: BlamePlayer[];
}

function ChampionAvatar({ name, size = 36 }: { name: string; size?: number }) {
  const [err, setErr] = useState(false);
  return (
    <div className="rounded-lg overflow-hidden shrink-0"
      style={{ width: size, height: size, border: "1px solid var(--border)" }}>
      {!err ? (
        <img src={champIcon(name)} alt={name} className="w-full h-full object-cover"
          onError={() => setErr(true)} />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-xs font-bold"
          style={{ background: "var(--bg-hover)", color: "var(--gold)" }}>
          {name.slice(0, 2)}
        </div>
      )}
    </div>
  );
}

function WinCurve({ curve, playerTeam, blueWon }: { curve: CurvePoint[]; playerTeam: string; blueWon: boolean }) {
  const playerWon = playerTeam === "blue" ? blueWon : !blueWon;
  const lineColor = playerWon ? "#0bc4e3" : "#e84057";

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const p = payload[0].value as number;
    return (
      <div className="card-shine rounded-lg p-3 text-xs space-y-1" style={{ minWidth: 140 }}>
        <p style={{ color: "var(--muted)" }}>{label} min</p>
        <p className="font-bold text-sm" style={{ color: p > 50 ? "#0bc4e3" : "#e84057" }}>
          {p.toFixed(1)}% win
        </p>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={curve} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        <defs>
          <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={lineColor} stopOpacity={0.2} />
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
        <Area type="monotone" dataKey="player_win_prob"
          stroke={lineColor} strokeWidth={2.5}
          fill="url(#grad)" dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function BlameRow({ player }: { player: BlamePlayer }) {
  const maxImpact = 80;
  const barW = Math.min(Math.abs(player.impact_score) / maxImpact * 100, 100);
  const accent = player.impact_score > 0 ? "var(--blue)" : "var(--red)";

  return (
    <div className="flex items-center gap-3 py-3"
      style={{ borderBottom: "1px solid var(--border)" }}>
      <ChampionAvatar name={player.champion} size={36} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1">
          <div className="min-w-0">
            <span className="font-bold text-sm truncate block">{player.champion}</span>
            <span className="text-xs truncate block" style={{ color: "var(--muted)" }}>{player.name}</span>
          </div>
          <span className="font-mono text-xs shrink-0 ml-2" style={{ color: "var(--muted)" }}>
            {player.kda_str}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--bg)" }}>
            <div className="h-full rounded-full transition-all"
              style={{ width: `${barW}%`, background: accent }} />
          </div>
          <span className="text-xs font-bold font-mono shrink-0 w-12 text-right"
            style={{ color: accent }}>
            {player.impact_score > 0 ? "+" : ""}{player.impact_score}
          </span>
        </div>
        <div className="flex gap-3 mt-1">
          <span className="text-xs" style={{ color: "var(--muted)" }}>KP {player.kill_participation}%</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>CS {player.cs}</span>
          <span className="text-xs" style={{ color: "var(--muted)" }}>{player.wards_placed}w</span>
        </div>
      </div>
    </div>
  );
}

export default function GamePage({ params }: { params: Promise<{ matchId: string }> }) {
  const { matchId } = use(params);
  const searchParams = useSearchParams();
  const router = useRouter();
  const playerTeam = searchParams.get("team") ?? "blue";

  const [data, setData] = useState<GameData | null>(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"curve" | "blame">("curve");

  useEffect(() => {
    initDDragon();
    fetch(`${API}/game/${matchId}?player_team=${playerTeam}`)
      .then(r => r.json())
      .then(setData)
      .finally(() => setLoading(false));
  }, [matchId, playerTeam]);

  if (loading) return (
    <main className="min-h-screen flex items-center justify-center gap-3" style={{ color: "var(--muted)" }}>
      <Loader2 size={20} className="animate-spin" style={{ color: "var(--gold)" }} />
      Analyse en cours...
    </main>
  );

  if (!data) return (
    <main className="min-h-screen flex items-center justify-center" style={{ color: "var(--red)" }}>
      Partie introuvable.
    </main>
  );

  const playerWon = playerTeam === "blue" ? data.blue_won : !data.blue_won;
  const resultColor = playerWon ? "var(--blue)" : "var(--red)";

  const tipping = data.curve.find(p => p.player_win_prob > 75 || p.player_win_prob < 25);

  // Ton équipe = la team du joueur, Équipe adverse = l'autre
  const myTeam  = data.blame.filter(p => p.team === playerTeam).sort((a, b) => b.impact_score - a.impact_score);
  const oppTeam = data.blame.filter(p => p.team !== playerTeam).sort((a, b) => b.impact_score - a.impact_score);

  const TABS = [
    { id: "curve" as const, label: "Courbe win %", icon: <TrendingUp size={14} /> },
    { id: "blame" as const, label: "Qui est fautif ?", icon: <Swords size={14} /> },
  ];

  return (
    <main className="min-h-screen px-4 py-10 max-w-5xl mx-auto">
      <button onClick={() => router.back()}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>
            Analyse post-game
          </p>
          <h1 className="text-3xl font-black" style={{ color: resultColor }}>
            {playerWon ? "Victoire" : "Défaite"}
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {data.duration_min} min
          </p>
        </div>
        {tipping && (
          <div className="card-shine rounded-xl p-4 text-right">
            <p className="text-xs" style={{ color: "var(--muted)" }}>Partie décidée à</p>
            <p className="text-2xl font-black" style={{ color: "var(--gold)" }}>{tipping.minute} min</p>
          </div>
        )}
      </div>

      <hr className="divider-gold mb-6" />

      {/* Tabs */}
      <div className="flex gap-1 mb-6 p-1 rounded-xl" style={{ background: "var(--bg-card)" }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-semibold transition-all"
            style={{
              background: tab === t.id ? "var(--bg-hover)" : "transparent",
              color: tab === t.id ? "var(--text)" : "var(--muted)",
              border: tab === t.id ? "1px solid var(--border)" : "1px solid transparent",
            }}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>

      {/* Curve tab */}
      {tab === "curve" && (
        <div className="space-y-4 max-w-2xl mx-auto">
          <div className="card-shine rounded-xl p-5">
            <p className="text-sm font-semibold mb-4" style={{ color: "var(--muted)" }}>
              Probabilité de victoire — minute par minute
            </p>
            <WinCurve curve={data.curve} playerTeam={playerTeam} blueWon={data.blue_won} />
          </div>

          {data.key_events.filter(e =>
            e.label.includes("Baron") || e.label.includes("Soul") || e.label.includes("Blood")
          ).length > 0 && (
            <div className="card-shine rounded-xl p-5">
              <p className="text-sm font-semibold mb-3" style={{ color: "var(--muted)" }}>Moments clés</p>
              <div className="space-y-2">
                {data.key_events.filter(e =>
                  e.label.includes("Baron") || e.label.includes("Soul") || e.label.includes("Blood")
                ).slice(0, 6).map((ev, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    <span className="text-xs px-2 py-0.5 rounded font-mono"
                      style={{ background: "var(--bg)", color: "var(--gold)" }}>
                      {ev.min}m
                    </span>
                    <span style={{ color: ev.team === "blue" ? "var(--blue)" : "var(--red)" }}>●</span>
                    <span>{ev.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Blame tab — 2 colonnes */}
      {tab === "blame" && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            {/* Ton équipe */}
            <div className="card-shine rounded-xl p-5">
              <div className="flex items-center gap-2 mb-1 pb-3"
                style={{ borderBottom: "1px solid var(--border)" }}>
                <Users size={14} style={{ color: playerWon ? "var(--blue)" : "var(--red)" }} />
                <span className="font-bold text-sm">Ton équipe</span>
                {playerWon
                  ? <Trophy size={13} className="ml-auto" style={{ color: "var(--gold)" }} />
                  : <Skull size={13} className="ml-auto" style={{ color: "var(--red)" }} />}
              </div>
              {myTeam.map(p => <BlameRow key={p.pid} player={p} />)}
            </div>

            {/* Équipe adverse */}
            <div className="card-shine rounded-xl p-5">
              <div className="flex items-center gap-2 mb-1 pb-3"
                style={{ borderBottom: "1px solid var(--border)" }}>
                <Swords size={14} style={{ color: playerWon ? "var(--red)" : "var(--blue)" }} />
                <span className="font-bold text-sm">Équipe adverse</span>
                {!playerWon
                  ? <Trophy size={13} className="ml-auto" style={{ color: "var(--gold)" }} />
                  : <Skull size={13} className="ml-auto" style={{ color: "var(--red)" }} />}
              </div>
              {oppTeam.map(p => <BlameRow key={p.pid} player={p} />)}
            </div>
          </div>

          <p className="text-xs text-center pb-2" style={{ color: "var(--muted)" }}>
            Score d&apos;impact = kill participation + vision − pénalité morts
          </p>
        </div>
      )}
    </main>
  );
}
