"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Search, Trophy, X, RefreshCw, Target } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const ROLES = [
  { key: "TOP",     label: "Top" },
  { key: "JUNGLE",  label: "Jungle" },
  { key: "MIDDLE",  label: "Mid" },
  { key: "BOTTOM",  label: "ADC" },
  { key: "UTILITY", label: "Support" },
];

interface ChampInfo { primary: string; viable: string[]; }
interface Candidate { champion: string; avg_synergy: number; meta_ratio: number; }
interface PuzzleResult {
  team: string[];
  role: string;
  role_display: string;
  answer: string;
  ranking: Candidate[];
}

// Génère un puzzle cohérent : 5 champions distincts, un par rôle,
// retire un rôle aléatoire → le puzzle affiche les 4 autres avec leurs rôles
function buildPuzzle(allChamps: Record<string, ChampInfo>) {
  // Pour chaque rôle, liste des champions dont ce rôle est viable (>= 5%)
  const byRole: Record<string, string[]> = {};
  for (const role of ROLES) {
    byRole[role.key] = Object.entries(allChamps)
      .filter(([, info]) => info.viable.includes(role.key))
      .map(([c]) => c);
  }

  const picked: Record<string, string> = {}; // role → champion
  const usedChamps = new Set<string>();

  for (const role of ROLES) {
    const pool = byRole[role.key].filter(c => !usedChamps.has(c));
    if (!pool.length) return null;
    const c = pool[Math.floor(Math.random() * pool.length)];
    picked[role.key] = c;
    usedChamps.add(c);
  }

  // Rôle manquant aléatoire
  const missingRole = ROLES[Math.floor(Math.random() * ROLES.length)];
  const team = ROLES
    .filter(r => r.key !== missingRole.key)
    .map(r => picked[r.key]);
  const teamWithRoles = ROLES
    .filter(r => r.key !== missingRole.key)
    .map(r => ({ champion: picked[r.key], role: r.label }));

  return {
    team,
    teamWithRoles,
    missingRole: missingRole.key,
    missingRoleLabel: missingRole.label,
  };
}

function rankOf(ranking: Candidate[], champ: string): number {
  return ranking.findIndex(c => c.champion === champ) + 1;
}

function scoreFromRank(rank: number, total: number): number {
  if (rank <= 0) return 0;
  if (rank === 1) return 100;
  if (rank <= 3) return 90;
  if (rank <= 5) return 75;
  if (rank <= 10) return 55;
  return Math.round(Math.max(0, (total - rank) / total * 40));
}

function ChampSearch({
  allChamps, role, usedChamps, onSelect,
}: {
  allChamps: Record<string, ChampInfo>;
  role: string;
  usedChamps: Set<string>;
  onSelect: (c: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  // Méta dans ce rôle d'abord
  const filtered = Object.keys(allChamps)
    .filter(c => c.toLowerCase().includes(query.toLowerCase()) && !usedChamps.has(c))
    .sort((a, b) => {
      const aV = allChamps[a]?.viable.includes(role) ? 0 : 1;
      const bV = allChamps[b]?.viable.includes(role) ? 0 : 1;
      if (aV !== bV) return aV - bV;
      return a.localeCompare(b);
    })
    .slice(0, 10);

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center gap-2 rounded-xl px-4 py-3 card-shine glow-gold">
        <Search size={16} style={{ color: "var(--gold)" }} />
        <input
          autoFocus
          className="flex-1 bg-transparent text-base outline-none placeholder:opacity-30"
          placeholder={`Champion ${ROLES.find(r => r.key === role)?.label ?? role}...`}
          value={query}
          onChange={e => { setQuery(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
        />
        {query && (
          <button onClick={() => setQuery("")}>
            <X size={14} style={{ color: "var(--muted)" }} />
          </button>
        )}
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute z-50 top-full mt-1 w-full rounded-xl overflow-hidden shadow-xl"
          style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
          {filtered.map(c => {
            const meta = allChamps[c]?.viable.includes(role);
            return (
              <button key={c}
                className="w-full text-left px-4 py-2.5 text-sm hover:bg-white/5 transition-colors flex items-center justify-between"
                onMouseDown={() => { onSelect(c); setQuery(""); setOpen(false); }}>
                <span style={{ color: "var(--text)" }}>{c}</span>
                {!meta && <span style={{ color: "var(--red)", fontSize: 10 }}>off-meta</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function SynergyPage() {
  const router = useRouter();
  const [allChamps, setAllChamps] = useState<Record<string, ChampInfo>>({});
  const [puzzle, setPuzzle] = useState<ReturnType<typeof buildPuzzle> | null>(null);
  const [serverResult, setServerResult] = useState<PuzzleResult | null>(null);
  const [guess, setGuess] = useState<string | null>(null);
  const [score, setScore] = useState<number | null>(null);
  const [loadingPuzzle, setLoadingPuzzle] = useState(true);
  const [streak, setStreak] = useState(0);
  const [bestStreak, setBestStreak] = useState(0);

  useEffect(() => {
    fetch(`${API}/champions`)
      .then(r => r.json())
      .then(d => {
        setAllChamps(d.champions);
        initPuzzle(d.champions);
      });
  }, []);

  function initPuzzle(champs: Record<string, ChampInfo>) {
    const p = buildPuzzle(champs);
    if (!p) return;
    setPuzzle(p);
    setLoadingPuzzle(true);
    fetch(`${API}/draft/puzzle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ team: p.team, role: p.missingRole }),
    })
      .then(r => r.json())
      .then(d => setServerResult(d))
      .finally(() => setLoadingPuzzle(false));
  }

  function handleGuess(c: string) {
    if (guess || !serverResult) return;
    setGuess(c);
    const rank = rankOf(serverResult.ranking, c);
    const s = scoreFromRank(rank, serverResult.ranking.length);
    setScore(s);
    if (s >= 75) {
      const next = streak + 1;
      setStreak(next);
      setBestStreak(prev => Math.max(prev, next));
    } else {
      setStreak(0);
    }
  }

  function nextPuzzle() {
    if (!Object.keys(allChamps).length) return;
    setGuess(null);
    setScore(null);
    setServerResult(null);
    initPuzzle(allChamps);
  }

  const isCorrect = guess && serverResult && guess === serverResult.answer;
  const guessRank = guess && serverResult ? rankOf(serverResult.ranking, guess) : 0;

  return (
    <main className="min-h-screen px-4 py-10 max-w-xl mx-auto">
      <button onClick={() => router.push("/")}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      {/* Header */}
      <div className="mb-6 flex items-start justify-between">
        <div>
          <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>Mini-jeu</p>
          <h1 className="text-4xl font-black text-gold-gradient">Synergie</h1>
          <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
            Trouve le meilleur pick pour compléter l&apos;équipe.
          </p>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1.5 justify-end">
            <Trophy size={14} style={{ color: "var(--gold)" }} />
            <span className="text-xl font-black" style={{ color: "var(--gold)" }}>{streak}</span>
          </div>
          <p className="text-xs" style={{ color: "var(--muted)" }}>streak</p>
          {bestStreak > 0 && (
            <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>best: {bestStreak}</p>
          )}
        </div>
      </div>

      {loadingPuzzle ? (
        <div className="flex items-center gap-3 py-20 justify-center" style={{ color: "var(--muted)" }}>
          <Loader2 size={20} className="animate-spin" style={{ color: "var(--gold)" }} />
          Génération du puzzle...
        </div>
      ) : puzzle && (
        <>
          {/* Team display */}
          <div className="card-shine rounded-xl p-5 mb-4">
            <p className="text-xs font-semibold tracking-widest uppercase mb-4" style={{ color: "var(--muted)" }}>
              Rôle manquant :{" "}
              <span style={{ color: "var(--gold)" }}>{puzzle.missingRoleLabel}</span>
            </p>
            <div className="grid grid-cols-5 gap-2">
              {puzzle.teamWithRoles.map(({ champion, role }, i) => (
                <div key={i} className="rounded-lg p-2 text-center"
                  style={{ background: "var(--bg)", border: "1px solid var(--border)" }}>
                  <p className="text-xs font-semibold leading-tight" style={{ color: "var(--text)" }}>{champion}</p>
                  <p className="text-xs mt-0.5" style={{ color: "var(--muted)", fontSize: 9 }}>{role}</p>
                </div>
              ))}
              {/* Slot vide */}
              <div className="rounded-lg p-2 text-center flex flex-col items-center justify-center gap-1"
                style={{ background: "rgba(200,155,60,0.08)", border: "2px dashed rgba(200,155,60,0.4)" }}>
                <Target size={16} style={{ color: "var(--gold)" }} />
                <p className="text-xs" style={{ color: "var(--gold)", fontSize: 9 }}>{puzzle.missingRoleLabel}</p>
              </div>
            </div>
          </div>

          {/* Input */}
          {!guess && (
            <ChampSearch
              allChamps={allChamps}
              role={puzzle.missingRole}
              usedChamps={new Set(puzzle.team)}
              onSelect={handleGuess}
            />
          )}

          {/* Résultat */}
          {guess && serverResult && score !== null && (
            <div className="space-y-3">
              {/* Score */}
              <div className="rounded-xl p-5 text-center"
                style={{
                  background: isCorrect
                    ? "rgba(11,196,227,0.1)" : score >= 75
                    ? "rgba(11,196,227,0.07)" : score >= 55
                    ? "rgba(200,155,60,0.08)" : "rgba(232,64,87,0.08)",
                  border: `1px solid ${isCorrect
                    ? "rgba(11,196,227,0.4)" : score >= 55
                    ? "rgba(200,155,60,0.3)" : "rgba(232,64,87,0.3)"}`,
                }}>
                <p className="text-5xl font-black tabular-nums mb-1"
                  style={{ color: isCorrect ? "var(--blue)" : score >= 55 ? "var(--gold)" : "var(--red)" }}>
                  {score}<span className="text-2xl">pts</span>
                </p>
                <p className="text-sm font-semibold"
                  style={{ color: isCorrect ? "var(--blue)" : score >= 55 ? "var(--gold)" : "var(--red)" }}>
                  {isCorrect ? "Parfait !" : score >= 75 ? "Excellent !" : score >= 55 ? "Pas mal !" : "Raté..."}
                </p>
                <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
                  Ton pick : <b style={{ color: "var(--text)" }}>{guess}</b>
                  {!isCorrect && guessRank > 0 && ` — rang #${guessRank} sur ${serverResult.ranking.length}`}
                </p>
              </div>

              {/* Réponse */}
              {!isCorrect && (
                <div className="rounded-xl p-4"
                  style={{ background: "rgba(11,196,227,0.06)", border: "1px solid rgba(11,196,227,0.2)" }}>
                  <p className="text-xs" style={{ color: "var(--muted)" }}>
                    Meilleure synergie ({serverResult.role_display}) :
                  </p>
                  <p className="text-lg font-black mt-0.5" style={{ color: "var(--blue)" }}>
                    {serverResult.answer}
                    <span className="text-sm font-normal ml-2" style={{ color: "var(--muted)" }}>
                      — {serverResult.ranking[0]?.avg_synergy.toFixed(1)}% avg
                    </span>
                  </p>
                </div>
              )}

              {/* Top 5 */}
              <div className="card-shine rounded-xl p-4">
                <p className="text-xs font-semibold tracking-widest uppercase mb-3" style={{ color: "var(--muted)" }}>
                  Top 5 synergies ({serverResult.role_display})
                </p>
                <div className="space-y-2">
                  {serverResult.ranking.slice(0, 5).map((c, i) => {
                    const isGuess  = c.champion === guess;
                    const isAnswer = c.champion === serverResult.answer;
                    return (
                      <div key={c.champion} className="flex items-center gap-3">
                        <span className="text-xs font-black w-5 text-center tabular-nums"
                          style={{ color: i === 0 ? "var(--gold)" : "var(--muted)" }}>
                          {i + 1}
                        </span>
                        <div className="flex-1 rounded-lg px-3 py-1.5 text-sm"
                          style={{
                            background: isGuess ? "rgba(200,155,60,0.12)" : "var(--bg)",
                            border: `1px solid ${isGuess ? "rgba(200,155,60,0.4)" : "var(--border)"}`,
                            color: isAnswer ? "var(--blue)" : "var(--text)",
                            fontWeight: (isGuess || isAnswer) ? 700 : 400,
                          }}>
                          {c.champion}{isGuess && !isAnswer && " (ton pick)"}{isAnswer && " ✓"}
                        </div>
                        <div className="text-right">
                          <p className="text-xs tabular-nums" style={{ color: "var(--muted)" }}>
                            {c.avg_synergy.toFixed(1)}%
                          </p>
                          <p className="text-xs" style={{ color: "var(--muted)", fontSize: 9 }}>
                            {c.meta_ratio.toFixed(0)}% méta
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <button onClick={nextPuzzle}
                className="w-full py-3 rounded-xl text-sm font-bold flex items-center justify-center gap-2"
                style={{ background: "linear-gradient(135deg,#c89b3c,#8a6d2a)", color: "#070b14" }}>
                <RefreshCw size={14} /> Puzzle suivant
              </button>
            </div>
          )}
        </>
      )}

      <div className="mt-8 text-center">
        <button onClick={() => router.push("/draft")}
          className="text-sm opacity-50 hover:opacity-100 transition-opacity font-semibold"
          style={{ color: "var(--gold)" }}>
          Draft Tester →
        </button>
      </div>
    </main>
  );
}
