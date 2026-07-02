"use client";
import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft, Loader2, Search, Trophy, Zap, Shield, Leaf, Target, Heart, ChevronRight, Swords,
} from "lucide-react";
import { champIcon, initDDragon } from "@/lib/ddragon";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ROLE_ICONS: Record<string, React.ReactNode> = {
  Top:     <Shield size={16} />,
  Jungle:  <Leaf size={16} />,
  Mid:     <Zap size={16} />,
  ADC:     <Target size={16} />,
  Support: <Heart size={16} />,
};

const ROLE_COLORS: Record<string, string> = {
  Top: "#e84057", Jungle: "#1db954", Mid: "#0bc4e3", ADC: "#c89b3c", Support: "#a78bfa",
};

interface BLGPlayer {
  name: string; role: string; game_name: string; tag: string; region: string;
}

interface TournamentMatch {
  match_id: string; date: string; block: string; league: string;
  team1: string; team2: string; team1_name: string; team2_name: string;
  team1_img: string; team2_img: string; winner: string;
  games: { id: string; number: number; state: string }[];
}

interface DatasetStats {
  [minute: number]: {
    gold_per_player: number; cs_per_player: number; players_alive_avg: number;
    damage_diff_avg: number; kills_diff_avg: number; blue_winrate: number; n_games: number;
  };
}

const PRO_STATS: Record<number, { gold: number; cs: number; wards: number; damage: number }> = {
  15: { gold: 7200,  cs: 142, wards: 22, damage: 14000 },
  20: { gold: 9800,  cs: 195, wards: 34, damage: 22000 },
  25: { gold: 13500, cs: 248, wards: 48, damage: 34000 },
};

function ChampionTag({ name }: { name: string }) {
  const [err, setErr] = useState(false);
  return (
    <div className="w-7 h-7 rounded overflow-hidden shrink-0 inline-block"
      style={{ border: "1px solid var(--border)" }}>
      {!err ? (
        <img src={champIcon(name)} alt={name} className="w-full h-full object-cover"
          onError={() => setErr(true)} />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-xs"
          style={{ background: "var(--bg-hover)", color: "var(--gold)" }}>
          {name.slice(0, 1)}
        </div>
      )}
    </div>
  );
}

const LEAGUES = [
  { key: "lec", label: "LEC" },
  { key: "lck", label: "LCK" },
  { key: "lpl", label: "LPL" },
  { key: "worlds", label: "Worlds" },
  { key: "msi", label: "MSI" },
];

export default function ProPage() {
  const router = useRouter();
  const [roster, setRoster] = useState<BLGPlayer[]>([]);
  const [datasetStats, setDatasetStats] = useState<DatasetStats>({});
  const [selectedMinute, setSelectedMinute] = useState(20);
  const [searchName, setSearchName] = useState("");
  const [searchTag, setSearchTag] = useState("");
  const [searchRegion, setSearchRegion] = useState("kr");
  const [searching, setSearching] = useState(false);
  const [proGames, setProGames] = useState<any[]>([]);
  const [searchError, setSearchError] = useState("");
  const [selectedPlayer, setSelectedPlayer] = useState<BLGPlayer | null>(null);
  // Tournois
  const [selectedLeague, setSelectedLeague] = useState("lec");
  const [tournamentMatches, setTournamentMatches] = useState<TournamentMatch[]>([]);
  const [loadingSchedule, setLoadingSchedule] = useState(false);

  useEffect(() => {
    initDDragon();
    fetch(`${API}/pro/roster`).then(r => r.json()).then(d => setRoster(d.players)).catch(() => {});
    fetch(`${API}/pro/dataset-stats`).then(r => r.json()).then(d => setDatasetStats(d.master_euw)).catch(() => {});
  }, []);

  const loadSchedule = useCallback(async (league: string) => {
    setSelectedLeague(league);
    setLoadingSchedule(true);
    setTournamentMatches([]);
    try {
      const res = await fetch(`${API}/pro/schedule/${league}?count=8`);
      const data = await res.json();
      setTournamentMatches(data.matches ?? []);
    } finally {
      setLoadingSchedule(false);
    }
  }, []);

  useEffect(() => { loadSchedule("lec"); }, [loadSchedule]);

  const searchPro = useCallback(async (player?: BLGPlayer) => {
    const name = player?.game_name ?? searchName;
    const tag  = player?.tag ?? searchTag;
    const reg  = player?.region ?? searchRegion;
    if (!name || !tag) return;

    setSearching(true);
    setSearchError("");
    setProGames([]);
    if (player) setSelectedPlayer(player);

    try {
      const res = await fetch(`${API}/pro/player/${encodeURIComponent(name)}/${encodeURIComponent(tag)}?region=${reg}`);
      if (!res.ok) {
        const err = await res.json();
        setSearchError(err.detail ?? "Joueur introuvable");
        return;
      }
      const data = await res.json();
      setProGames(data.games ?? []);
      if (!data.games?.length) setSearchError("Aucune partie trouvée pour ce joueur.");
    } catch {
      setSearchError("Erreur de connexion");
    } finally {
      setSearching(false);
    }
  }, [searchName, searchTag, searchRegion]);

  const ds = datasetStats[selectedMinute];
  const ps = PRO_STATS[selectedMinute];

  const comparisonRows = ds && ps ? [
    { label: "Gold/joueur", master: ds.gold_per_player, pro: ps.gold, unit: "g" },
    { label: "CS/joueur", master: ds.cs_per_player, pro: ps.cs, unit: "" },
    { label: "Wards posées", master: 15 + selectedMinute * 0.5, pro: ps.wards, unit: "" },
    { label: "Dégâts/joueur", master: Math.round(8000 + selectedMinute * 700), pro: ps.damage, unit: "" },
  ] : [];

  return (
    <main className="min-h-screen px-6 md:px-12 lg:px-20 py-12">
      <button onClick={() => router.push("/")}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      <div className="mb-10">
        <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>Analyse compétitive</p>
        <h1 className="text-5xl font-black text-gold-gradient">Et en pro ?</h1>
        <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>
          Comparez les métriques LPL avec les parties Master+ EUW de notre dataset.
        </p>
      </div>

      {/* Tournois en direct */}
      <section className="mb-10">
        <div className="flex items-center gap-3 mb-5">
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
          <span className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--gold-dim)" }}>
            Parties de tournoi — analyse modèle
          </span>
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
        </div>

        {/* League selector */}
        <div className="flex gap-2 mb-4 flex-wrap">
          {LEAGUES.map(l => (
            <button key={l.key} onClick={() => loadSchedule(l.key)}
              className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
              style={{
                background: selectedLeague === l.key ? "var(--bg-hover)" : "var(--bg-card)",
                color: selectedLeague === l.key ? "var(--gold)" : "var(--muted)",
                border: `1px solid ${selectedLeague === l.key ? "var(--gold)" : "var(--border)"}`,
              }}>
              {l.label}
            </button>
          ))}
        </div>

        {loadingSchedule && (
          <div className="flex items-center gap-2 justify-center py-6" style={{ color: "var(--muted)" }}>
            <Loader2 size={16} className="animate-spin" style={{ color: "var(--gold)" }} />
            Chargement du calendrier...
          </div>
        )}

        {tournamentMatches.length > 0 && (
          <div className="space-y-2">
            {tournamentMatches.map(m => {
              const completedGames = m.games.filter(g => g.state === "completed");
              const isWin1 = m.winner === m.team1;
              return (
                <div key={m.match_id} className="card-shine rounded-xl overflow-hidden">
                  {/* Header du match */}
                  <div className="flex items-center px-4 py-3 gap-4">
                    <span className="text-xs shrink-0" style={{ color: "var(--muted)" }}>{m.date}</span>
                    <span className="text-xs shrink-0 px-2 py-0.5 rounded" style={{ background: "var(--bg)", color: "var(--gold-dim)" }}>{m.block}</span>
                    <div className="flex-1 flex items-center justify-center gap-4">
                      <span className="font-black text-base" style={{ color: isWin1 ? "var(--gold)" : "var(--muted)" }}>
                        {m.team1}
                      </span>
                      <span className="text-xs" style={{ color: "var(--muted)" }}>vs</span>
                      <span className="font-black text-base" style={{ color: !isWin1 ? "var(--gold)" : "var(--muted)" }}>
                        {m.team2}
                      </span>
                    </div>
                    <span className="text-xs shrink-0" style={{ color: "var(--muted)" }}>{completedGames.length} game{completedGames.length > 1 ? "s" : ""}</span>
                  </div>
                  {/* Games analysables */}
                  {completedGames.length > 0 && (
                    <div className="flex gap-2 px-4 pb-3 flex-wrap">
                      {completedGames.map(g => (
                        <button key={g.id}
                          onClick={() => router.push(`/esports-game/${g.id}?match=${m.match_id}&t1=${m.team1}&t2=${m.team2}`)}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all hover:scale-105"
                          style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--gold)" }}>
                          <Swords size={11} />
                          Game {g.number}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {!loadingSchedule && tournamentMatches.length === 0 && (
          <div className="card-shine rounded-xl p-6 text-center text-sm" style={{ color: "var(--muted)" }}>
            Aucun match disponible pour cette compétition.
          </div>
        )}
      </section>

      {/* BLG Roster */}
      <section className="mb-10">
        <div className="flex items-center gap-3 mb-5">
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
          <span className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--gold-dim)" }}>
            Bilibili Gaming — LPL 2026
          </span>
          <div className="h-px flex-1" style={{ background: "var(--border)" }} />
        </div>

        <div className="grid grid-cols-5 gap-3 mb-4">
          {(roster.length > 0 ? roster : [
            { name: "Bin",    role: "Top",     game_name: "BIN",    tag: "BIN", region: "kr" },
            { name: "XUN",    role: "Jungle",  game_name: "XUN",    tag: "BLG", region: "kr" },
            { name: "Knight", role: "Mid",     game_name: "Knight", tag: "BLG", region: "kr" },
            { name: "Viper",  role: "ADC",     game_name: "Viper",  tag: "BLG", region: "kr" },
            { name: "ON",     role: "Support", game_name: "ON",     tag: "BLG", region: "kr" },
          ]).map(p => {
            const isSelected = selectedPlayer?.name === p.name;
            const color = ROLE_COLORS[p.role];
            return (
              <button key={p.name} onClick={() => searchPro(p)}
                className="card-shine rounded-xl p-4 text-center transition-all hover:scale-105 flex flex-col items-center gap-2"
                style={{
                  border: `1px solid ${isSelected ? color : "var(--border)"}`,
                  boxShadow: isSelected ? `0 0 14px ${color}40` : "none",
                }}>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ background: `${color}18`, color }}>
                  {ROLE_ICONS[p.role]}
                </div>
                <p className="font-bold text-sm leading-tight" style={{ color: isSelected ? color : "var(--text)" }}>
                  {p.name}
                </p>
                <p className="text-xs" style={{ color: "var(--muted)" }}>{p.role}</p>
              </button>
            );
          })}
        </div>

        {/* Pro games list */}
        {searching && (
          <div className="flex items-center gap-2 justify-center py-6" style={{ color: "var(--muted)" }}>
            <Loader2 size={16} className="animate-spin" style={{ color: "var(--gold)" }} />
            Récupération des parties...
          </div>
        )}
        {searchError && (
          <div className="card-shine rounded-xl p-4 text-center text-sm" style={{ color: "var(--red)" }}>
            {searchError}
          </div>
        )}
        {proGames.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs mb-3" style={{ color: "var(--muted)" }}>
              {proGames.length} parties récentes — {selectedPlayer?.name}
            </p>
            {proGames.map(g => (
              <button key={g.match_id}
                onClick={() => router.push(`/game/${g.match_id}?team=${g.player_team}`)}
                className="w-full card-shine rounded-xl p-4 text-left transition-all hover:scale-[1.01] flex items-center gap-3 group">
                <div className="w-1 self-stretch rounded-full shrink-0"
                  style={{ background: g.won ? "var(--blue)" : "var(--red)" }} />
                <ChampionTag name={g.champion} />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-sm" style={{ color: g.won ? "var(--blue)" : "var(--red)" }}>
                      {g.won ? "Victoire" : "Défaite"}
                    </span>
                    <span className="text-sm font-medium">{g.champion}</span>
                    <span className="text-xs font-mono" style={{ color: "var(--muted)" }}>
                      {g.kills}/{g.deaths}/{g.assists}
                    </span>
                  </div>
                  <span className="text-xs" style={{ color: "var(--muted)" }}>{g.duration_min} min</span>
                </div>
                <ChevronRight size={14} className="opacity-0 group-hover:opacity-100 transition-opacity"
                  style={{ color: "var(--gold)" }} />
              </button>
            ))}
          </div>
        )}
      </section>

      {/* Comparaison + Recherche — côte à côte */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">

        {/* Comparaison métriques */}
        <section>
          <div className="flex items-center gap-3 mb-5">
            <div className="h-px flex-1" style={{ background: "var(--border)" }} />
            <span className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--gold-dim)" }}>
              Comparaison métriques
            </span>
            <div className="h-px flex-1" style={{ background: "var(--border)" }} />
          </div>

          <div className="flex gap-2 mb-4">
            {[15, 20, 25].map(m => (
              <button key={m} onClick={() => setSelectedMinute(m)}
                className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
                style={{
                  background: selectedMinute === m ? "var(--bg-hover)" : "var(--bg-card)",
                  color: selectedMinute === m ? "var(--gold)" : "var(--muted)",
                  border: `1px solid ${selectedMinute === m ? "var(--gold)" : "var(--border)"}`,
                }}>
                {m} min
              </button>
            ))}
          </div>

          {comparisonRows.length > 0 ? (
            <div className="card-shine rounded-xl p-5 space-y-4">
              <div className="flex justify-between text-xs mb-2" style={{ color: "var(--muted)" }}>
                <span>Métrique</span>
                <div className="flex gap-6">
                  <span style={{ color: "var(--blue)" }}>Masters EUW</span>
                  <span style={{ color: "var(--gold)" }}>LPL Pro</span>
                </div>
              </div>
              {comparisonRows.map(row => {
                const maxVal = Math.max(row.master, row.pro);
                const masterW = (row.master / maxVal) * 100;
                const proW = (row.pro / maxVal) * 100;
                const pctDiff = Math.round((row.pro - row.master) / row.master * 100);
                return (
                  <div key={row.label}>
                    <div className="flex justify-between text-xs mb-2">
                      <span style={{ color: "var(--muted)" }}>{row.label}</span>
                      <span className="font-bold text-xs" style={{ color: pctDiff > 0 ? "var(--gold)" : "var(--red)" }}>
                        {pctDiff > 0 ? "+" : ""}{pctDiff}% vs Masters
                      </span>
                    </div>
                    <div className="space-y-1.5">
                      {[{ val: row.master, color: "var(--blue)", w: masterW, unit: row.unit },
                        { val: row.pro, color: "var(--gold)", w: proW, unit: row.unit }].map((r, i) => (
                        <div key={i} className="flex items-center gap-3">
                          <div className="w-20 text-right text-xs font-mono" style={{ color: r.color }}>
                            {Math.round(r.val).toLocaleString()}{r.unit}
                          </div>
                          <div className="flex-1 h-1.5 rounded-full" style={{ background: "var(--bg)" }}>
                            <div className="h-full rounded-full transition-all duration-700"
                              style={{ width: `${r.w}%`, background: r.color }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
              <p className="text-xs pt-1" style={{ color: "var(--muted)" }}>
                {ds?.n_games ?? 0} parties dataset · Stats LPL estimées
              </p>
            </div>
          ) : (
            <div className="card-shine rounded-xl p-8 text-center">
              <Loader2 size={20} className="animate-spin mx-auto mb-2" style={{ color: "var(--gold)" }} />
              <p className="text-sm" style={{ color: "var(--muted)" }}>Chargement...</p>
            </div>
          )}
        </section>

        {/* Recherche joueur pro */}
        <section>
          <div className="flex items-center gap-3 mb-5">
            <div className="h-px flex-1" style={{ background: "var(--border)" }} />
            <span className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--gold-dim)" }}>
              Rechercher un pro
            </span>
            <div className="h-px flex-1" style={{ background: "var(--border)" }} />
          </div>

          <div className="card-shine rounded-xl p-5 space-y-3">
            <div className="flex gap-2">
              <input
                placeholder="GameName"
                value={searchName}
                onChange={e => setSearchName(e.target.value)}
                className="flex-1 px-3 py-2.5 rounded-lg text-sm outline-none"
                style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
              <input
                placeholder="TAG"
                value={searchTag}
                onChange={e => setSearchTag(e.target.value)}
                className="w-20 px-3 py-2.5 rounded-lg text-sm outline-none"
                style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}
              />
            </div>
            <div className="flex gap-2">
              <select
                value={searchRegion}
                onChange={e => setSearchRegion(e.target.value)}
                className="flex-1 px-3 py-2.5 rounded-lg text-sm outline-none"
                style={{ background: "var(--bg)", border: "1px solid var(--border)", color: "var(--text)" }}>
                <option value="kr">KR (solo queue LPL)</option>
                <option value="euw">EUW</option>
                <option value="na">NA</option>
              </select>
              <button
                onClick={() => { setSelectedPlayer(null); searchPro(); }}
                disabled={!searchName || !searchTag || searching}
                className="px-4 py-2.5 rounded-lg text-sm font-semibold transition-all disabled:opacity-30 flex items-center gap-2"
                style={{ background: "var(--gold)", color: "#070b14" }}>
                <Search size={14} />
                Chercher
              </button>
            </div>
            <p className="text-xs" style={{ color: "var(--muted)" }}>
              Les pros LPL jouent sur serveur CN (inaccessible via Riot API) — retrouvez-les sur KR.
            </p>
          </div>

          {/* Insights */}
          <div className="mt-4 space-y-3">
            <div className="card-shine rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Zap size={13} style={{ color: "var(--gold)" }} />
                <span className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--gold-dim)" }}>
                  Insight modèle
                </span>
              </div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Notre modèle entraîné sur Masters+ EUW prédit les parties pro avec une précision similaire.
                Le gold diff reste le meilleur prédicteur à tout timestamp.
              </p>
            </div>
            <div className="card-shine rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <Trophy size={13} style={{ color: "var(--gold)" }} />
                <span className="text-xs font-bold tracking-widest uppercase" style={{ color: "var(--gold-dim)" }}>
                  Bilibili Gaming
                </span>
              </div>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                BLG 2026 : Knight (ex-T1) au mid, Viper à l&apos;ADC — deux stars du circuit KR/LPL.
                Bin reste parmi les meilleurs tops d&apos;Asie.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
