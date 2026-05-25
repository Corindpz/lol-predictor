"use client";
import { use, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft, Loader2, Trophy, Skull, TrendingUp, Swords, Users,
  Flame, Crown, Eye, Building, ShieldAlert, Star, Zap, Bug, TrendingDown,
} from "lucide-react";
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
interface KeyEvent { min: number; label: string; team: string; type: string; }
interface GameData {
  match_id: string; blue_won: boolean; duration_min: number;
  curve: CurvePoint[]; key_events: KeyEvent[]; blame: BlamePlayer[];
}

const EVENT_ICONS: Record<string, React.ReactNode> = {
  first_blood: <Swords size={12} />,
  dragon:      <Flame size={12} />,
  elder_dragon:<Zap size={12} />,
  dragon_soul: <Star size={12} />,
  baron:       <Crown size={12} />,
  rift_herald: <Eye size={12} />,
  tower:       <Building size={12} />,
  inhibitor:   <ShieldAlert size={12} />,
  teamfight:   <Users size={12} />,
  void_grub:   <Bug size={12} />,
  gold_swing:  <TrendingUp size={12} />,
};

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
    const gd = payload[1]?.value as number;
    return (
      <div className="card-shine rounded-lg p-3 text-xs space-y-1.5" style={{ minWidth: 150 }}>
        <p style={{ color: "var(--muted)" }}>{label} min</p>
        <p className="font-bold text-sm" style={{ color: p > 50 ? "#0bc4e3" : "#e84057" }}>
          {p.toFixed(1)}% win
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
          stroke={lineColor} strokeWidth={2.5} fill="url(#grad)" dot={false} />
        <Area type="monotone" dataKey="gold_diff" hide />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function EventRow({ event, playerTeam }: { event: KeyEvent; playerTeam: string }) {
  const isMyTeam = event.team === playerTeam;
  const accent = isMyTeam ? "var(--blue)" : "var(--red)";
  const icon = EVENT_ICONS[event.type] ?? <TrendingDown size={12} />;

  return (
    <div className="flex items-center gap-3 py-2.5"
      style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <span className="text-xs font-mono w-10 shrink-0 text-right" style={{ color: "var(--gold)" }}>
        {event.min}m
      </span>
      <span className="shrink-0" style={{ color: accent }}>{icon}</span>
      <span className="text-sm flex-1">{event.label}</span>
      <span className="text-xs px-2 py-0.5 rounded shrink-0"
        style={{ background: `${accent}15`, color: accent }}>
        {isMyTeam ? "Ton éq." : "Adversaire"}
      </span>
    </div>
  );
}

function BlameRow({ player, rank, teamWon }: { player: BlamePlayer; rank: number; teamWon: boolean }) {
  const isFautif = player.impact_score < -5;
  const isCarry  = player.impact_score > 15;
  const accent   = isCarry ? "var(--blue)" : isFautif ? "var(--red)" : "var(--muted)";
  const rowBg    = isCarry ? "rgba(11,196,227,0.04)" : isFautif ? "rgba(232,84,87,0.04)" : "transparent";
  const maxImpact = 80;
  const barW     = Math.min(Math.abs(player.impact_score) / maxImpact * 100, 100);

  // Badge pour 1er de chaque liste
  const badge = rank === 1
    ? teamWon ? "MVP" : "Fautif #1"
    : null;
  const badgeColor = teamWon ? "var(--gold)" : "var(--red)";

  return (
    <div className="flex items-center gap-3 py-3 px-2 rounded-lg transition-colors"
      style={{ borderBottom: "1px solid var(--border)", background: rowBg }}>
      <ChampionAvatar name={player.champion} size={34} />
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
        <p className="text-xs" style={{ color: "var(--muted)" }}>{player.kill_participation}% KP</p>
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

  // Tri : équipe qui perd → pire d'abord (fautif en haut) ; équipe qui gagne → meilleur d'abord
  const sortTeam = (players: BlamePlayer[], teamWon: boolean) =>
    [...players].sort((a, b) => teamWon
      ? b.impact_score - a.impact_score   // gagnants : meilleur d'abord
      : a.impact_score - b.impact_score   // perdants : pire d'abord (fautif #1 en haut)
    );

  const myTeamWon  = playerWon;
  const oppTeamWon = !playerWon;
  const myTeam  = sortTeam(data.blame.filter(p => p.team === playerTeam), myTeamWon);
  const oppTeam = sortTeam(data.blame.filter(p => p.team !== playerTeam), oppTeamWon);

  // Détection swings de gold depuis la courbe (variation > 1500g entre 2 minutes)
  const goldSwingEvents: KeyEvent[] = data.curve
    .filter((p, i) => i > 0 && Math.abs(p.gold_diff - data.curve[i - 1].gold_diff) > 1500)
    .map(p => ({
      min: p.minute,
      label: `Écart gold ${p.gold_diff >= 0 ? "+" : ""}${p.gold_diff.toLocaleString()}g`,
      team: p.gold_diff > 0 ? playerTeam : playerTeam === "blue" ? "red" : "blue",
      type: "gold_swing",
    }));

  const allEvents = [...data.key_events, ...goldSwingEvents].sort((a, b) => a.min - b.min);

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
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>
            Analyse post-game
          </p>
          <h1 className="text-3xl font-black" style={{ color: resultColor }}>
            {playerWon ? "Victoire" : "Défaite"}
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            {data.duration_min} min · {allEvents.length} événements clés
          </p>
        </div>
        {tipping && (
          <div className="card-shine rounded-xl p-4 text-right shrink-0">
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

      {/* ── Curve tab ── */}
      {tab === "curve" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Courbe */}
          <div className="lg:col-span-2 card-shine rounded-xl p-5">
            <p className="text-sm font-semibold mb-4" style={{ color: "var(--muted)" }}>
              Probabilité de victoire — minute par minute
            </p>
            <WinCurve curve={data.curve} playerTeam={playerTeam} blueWon={data.blue_won} />
          </div>

          {/* Timeline des events — colonne droite */}
          <div className="card-shine rounded-xl p-5 overflow-y-auto" style={{ maxHeight: 380 }}>
            <p className="text-sm font-semibold mb-2" style={{ color: "var(--muted)" }}>
              Moments clés
            </p>
            {allEvents.length === 0 ? (
              <p className="text-xs" style={{ color: "var(--muted)" }}>Aucun événement enregistré.</p>
            ) : (
              allEvents.map((ev, i) => (
                <EventRow key={i} event={ev} playerTeam={playerTeam} />
              ))
            )}
          </div>
        </div>
      )}

      {/* ── Blame tab ── */}
      {tab === "blame" && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-4">
            {/* Ton équipe */}
            <div className="card-shine rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3 pb-3"
                style={{ borderBottom: "1px solid var(--border)" }}>
                <Users size={14} style={{ color: myTeamWon ? "var(--blue)" : "var(--red)" }} />
                <span className="font-bold text-sm">Ton équipe</span>
                {myTeamWon
                  ? <Trophy size={13} className="ml-auto" style={{ color: "var(--gold)" }} />
                  : <Skull size={13} className="ml-auto" style={{ color: "var(--red)" }} />}
              </div>
              {myTeam.map((p, i) => (
                <BlameRow key={p.pid} player={p} rank={i + 1} teamWon={myTeamWon} />
              ))}
            </div>

            {/* Équipe adverse */}
            <div className="card-shine rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3 pb-3"
                style={{ borderBottom: "1px solid var(--border)" }}>
                <Swords size={14} style={{ color: oppTeamWon ? "var(--blue)" : "var(--red)" }} />
                <span className="font-bold text-sm">Équipe adverse</span>
                {oppTeamWon
                  ? <Trophy size={13} className="ml-auto" style={{ color: "var(--gold)" }} />
                  : <Skull size={13} className="ml-auto" style={{ color: "var(--red)" }} />}
              </div>
              {oppTeam.map((p, i) => (
                <BlameRow key={p.pid} player={p} rank={i + 1} teamWon={oppTeamWon} />
              ))}
            </div>
          </div>

          <p className="text-xs text-center pb-2" style={{ color: "var(--muted)" }}>
            Score d&apos;impact = kill participation + vision − pénalité morts
            · Perdants triés du plus au moins fautif
          </p>
        </div>
      )}
    </main>
  );
}
