"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, TrendingUp, Swords, Users, Database, Brain, Trophy, Puzzle, FlaskConical } from "lucide-react";

export default function Home() {
  const router = useRouter();
  const [riotId, setRiotId] = useState("");
  const [error, setError] = useState("");

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!riotId.includes("#")) { setError("Format invalide — utilisez GameName#TAG"); return; }
    const slug = riotId.replace("#", "-");
    router.push(`/player/${encodeURIComponent(slug)}`);
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 relative overflow-hidden py-16">

      {/* Ambient glows */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute top-[-20%] left-[10%] w-[700px] h-[700px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(200,155,60,0.08) 0%, transparent 70%)" }} />
        <div className="absolute bottom-[-10%] right-[5%] w-[600px] h-[600px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(11,196,227,0.06) 0%, transparent 70%)" }} />
      </div>

      <div className="z-10 w-full max-w-2xl flex flex-col items-center gap-10">

        {/* Title block */}
        <div className="text-center space-y-4">
          <p className="text-xs tracking-[0.35em] uppercase" style={{ color: "var(--gold-dim)" }}>
            Projet fil rouge · B3 IA &amp; Data · Ynov 2026
          </p>
          <h1 className="text-8xl font-black tracking-tight leading-none text-gold-gradient">
            PREDICT.GG
          </h1>
          <p style={{ color: "var(--muted)" }} className="text-lg max-w-md mx-auto">
            À quelle minute votre partie était-elle déjà jouée ?
          </p>
        </div>

        <hr className="divider-gold w-32" />

        {/* Search */}
        <form onSubmit={handleSearch} className="w-full space-y-2">
          <div className="card-shine rounded-xl p-1.5 flex items-center gap-2 glow-gold">
            <Search size={18} className="ml-3 shrink-0" style={{ color: "var(--gold)" }} />
            <input
              type="text"
              value={riotId}
              onChange={e => { setRiotId(e.target.value); setError(""); }}
              placeholder="GameName#TAG"
              className="flex-1 bg-transparent py-3 pr-3 outline-none text-lg placeholder:opacity-30"
              autoFocus
            />
            <button type="submit" disabled={!riotId}
              className="shrink-0 px-6 py-3 rounded-lg text-sm font-bold transition-all disabled:opacity-30"
              style={{ background: "linear-gradient(135deg,#c89b3c,#8a6d2a)", color: "#070b14" }}>
              Analyser
            </button>
          </div>
          {error && <p className="text-sm text-center" style={{ color: "var(--red)" }}>{error}</p>}
        </form>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-3">
          {[
            { icon: <TrendingUp size={14} />, label: "Win % minute par minute" },
            { icon: <Swords size={14} />, label: "Simulateur de partie" },
            { icon: <Users size={14} />, label: "Qui est le fautif ?" },
            { icon: <Trophy size={14} />, label: "Analyse pro LPL" },
            { icon: <FlaskConical size={14} />, label: "Draft Tester" },
            { icon: <Puzzle size={14} />, label: "Mini-jeu Synergie" },
          ].map(f => (
            <span key={f.label}
              className="flex items-center gap-2 px-4 py-2 rounded-full text-sm"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--muted)" }}>
              <span style={{ color: "var(--gold)" }}>{f.icon}</span>{f.label}
            </span>
          ))}
        </div>

        {/* Nav links */}
        <div className="flex flex-wrap items-center justify-center gap-6">
          <button onClick={() => router.push("/simulator")}
            className="text-sm opacity-50 hover:opacity-100 transition-opacity font-semibold"
            style={{ color: "var(--gold)" }}>
            Simulateur →
          </button>
          <span style={{ color: "var(--border)" }}>|</span>
          <button onClick={() => router.push("/pro")}
            className="text-sm opacity-50 hover:opacity-100 transition-opacity font-semibold"
            style={{ color: "var(--gold)" }}>
            Et en pro ? →
          </button>
          <span style={{ color: "var(--border)" }}>|</span>
          <button onClick={() => router.push("/draft")}
            className="text-sm opacity-50 hover:opacity-100 transition-opacity font-semibold"
            style={{ color: "var(--gold)" }}>
            Draft Tester →
          </button>
          <span style={{ color: "var(--border)" }}>|</span>
          <button onClick={() => router.push("/synergy")}
            className="text-sm opacity-50 hover:opacity-100 transition-opacity font-semibold"
            style={{ color: "var(--gold)" }}>
            Mini-jeu →
          </button>
        </div>

        {/* Dataset stats strip */}
        <div className="w-full grid grid-cols-3 gap-3 pt-2">
          {[
            { icon: <Database size={14} />, value: "25 349",  label: "snapshots" },
            { icon: <Brain size={14} />,    value: "77.2%",   label: "accuracy" },
            { icon: <TrendingUp size={14} />,value: "AUC 0.856", label: "XGBoost calibré" },
          ].map(s => (
            <div key={s.label} className="card-shine rounded-xl p-4 text-center">
              <div className="flex items-center justify-center gap-1.5 mb-1"
                style={{ color: "var(--gold)" }}>
                {s.icon}
              </div>
              <p className="font-black text-xl" style={{ color: "var(--text)" }}>{s.value}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
