"use client";
import { use, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Loader2, Trophy, Skull } from "lucide-react";
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

function BlameCard({ player, rank }: { player: BlamePlayer; rank: number }) {
  const isWinner = player.won;
  const accent = isWinner ? "var(--blue)" : "var(--red)";
  const maxImpact = 100;
  const barWidth = Math.min(Math.abs(player.impact_score) / maxImpact * 100, 100);

  return (
    <div className="card-shine rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-3">
        <span className="text-2xl font-black opacity-20">#{rank}</span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-bold text-sm">{player.champion}</span>
            <span className="text-xs px-2 py-0.5 rounded-full"
              style={{ background: `${accent}15`, color: accent, border: `1px solid ${accent}33` }}>
              {isWinner ? "Carry" : "Fautif"}
            </span>
          </div>
          <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{player.name}</p>
        </div>
        <div className="text-right">
          <p className="font-bold text-sm">{player.kda_str}</p>
          <p className="text-xs" style={{ color: "var(--muted)" }}>KDA</p>
        </div>
      </div>

      {/* Impact bar */}
      <div>
        <div className="flex justify-between text-xs mb-1" style={{ color: "var(--muted)" }}>
          <span>Impact score</span>
          <span style={{ color: accent }}>{player.impact_score > 0 ? "+" : ""}{player.impact_score}</span>
        </div>
        <div className="h-1.5 rounded-full" style={{ background: "var(--bg)" }}>
          <div className="h-full rounded-full transition-all"
            style={{ width: `${barWidth}%`, background: accent }} />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-2 text-center">
        {[
          { label: "Kill Part.", value: `${player.kill_participation}%` },
          { label: "Wards", value: player.wards_placed },
          { label: "CS", value: player.cs },
        ].map(s => (
          <div key={s.label} className="rounded-lg py-2 px-1"
            style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
            <p className="text-sm font-bold">{s.value}</p>
            <p className="text-xs" style={{ color: "var(--muted)" }}>{s.label}</p>
          </div>
        ))}
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

  if (!data) return <main className="min-h-screen flex items-center justify-center" style={{ color: "var(--red)" }}>Partie introuvable.</main>;

  const playerWon = playerTeam === "blue" ? data.blue_won : !data.blue_won;
  const resultColor = playerWon ? "var(--blue)" : "var(--red)";

  // Tipping point : première minute avec prob > 75 ou < 25
  const tipping = data.curve.find(p => p.player_win_prob > 75 || p.player_win_prob < 25);

  // Blame séparé par équipe
  const blueTeam = data.blame.filter(p => p.team === "blue").sort((a, b) => b.impact_score - a.impact_score);
  const redTeam  = data.blame.filter(p => p.team === "red").sort((a, b) => b.impact_score - a.impact_score);

  return (
    <main className="min-h-screen px-4 py-10 max-w-2xl mx-auto">
      <button onClick={() => router.back()}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>Analyse post-game</p>
          <h1 className="text-3xl font-black" style={{ color: resultColor }}>
            {playerWon ? "Victoire" : "Défaite"}
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {data.duration_min} min · Équipe {playerTeam === "blue" ? "Bleue" : "Rouge"}
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
        {(["curve", "blame"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className="flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all"
            style={{
              background: tab === t ? "var(--bg-hover)" : "transparent",
              color: tab === t ? "var(--text)" : "var(--muted)",
              border: tab === t ? "1px solid var(--border)" : "1px solid transparent",
            }}>
            {t === "curve" ? "📈 Courbe win %" : "⚔️ Qui est le fautif ?"}
          </button>
        ))}
      </div>

      {/* Curve tab */}
      {tab === "curve" && (
        <div className="space-y-4">
          <div className="card-shine rounded-xl p-5">
            <p className="text-sm font-semibold mb-4" style={{ color: "var(--muted)" }}>
              Probabilité de victoire — minute par minute
            </p>
            <WinCurve curve={data.curve} playerTeam={playerTeam} blueWon={data.blue_won} />
          </div>

          {/* Key events */}
          {data.key_events.length > 0 && (
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

      {/* Blame tab */}
      {tab === "blame" && (
        <div className="space-y-6">
          {[
            { label: "🔵 Équipe Bleue", players: blueTeam, won: data.blue_won },
            { label: "🔴 Équipe Rouge", players: redTeam, won: !data.blue_won },
          ].map(team => (
            <div key={team.label}>
              <div className="flex items-center gap-2 mb-3">
                <span className="font-bold text-sm">{team.label}</span>
                {team.won
                  ? <Trophy size={14} style={{ color: "var(--gold)" }} />
                  : <Skull size={14} style={{ color: "var(--red)" }} />}
              </div>
              <div className="space-y-2">
                {team.players.map((p, i) => <BlameCard key={p.pid} player={p} rank={i + 1} />)}
              </div>
            </div>
          ))}
          <p className="text-xs text-center pb-4" style={{ color: "var(--muted)" }}>
            Score d&apos;impact = kill participation + vision − pénalité morts
          </p>
        </div>
      )}
    </main>
  );
}
