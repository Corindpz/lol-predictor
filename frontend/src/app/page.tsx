"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, TrendingUp, Swords, Users } from "lucide-react";

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
    <main className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden">

      {/* Ambient glows */}
      <div className="pointer-events-none fixed inset-0 z-0">
        <div className="absolute top-[-20%] left-[10%] w-[600px] h-[600px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(200,155,60,0.07) 0%, transparent 70%)" }} />
        <div className="absolute bottom-[-10%] right-[5%] w-[500px] h-[500px] rounded-full"
          style={{ background: "radial-gradient(circle, rgba(11,196,227,0.05) 0%, transparent 70%)" }} />
      </div>

      <div className="z-10 w-full max-w-xl flex flex-col items-center gap-10">

        {/* Title block */}
        <div className="text-center space-y-3">
          <p className="text-xs tracking-[0.3em] uppercase" style={{ color: "var(--gold-dim)" }}>
            Projet fil rouge · B3 IA &amp; Data · Ynov 2026
          </p>
          <h1 className="text-7xl font-black tracking-tight leading-none text-gold-gradient">
            PREDICT.GG
          </h1>
          <p style={{ color: "var(--muted)" }} className="text-base">
            À quelle minute votre partie était-elle déjà jouée ?
          </p>
        </div>

        <hr className="divider-gold w-32" />

        {/* Search */}
        <form onSubmit={handleSearch} className="w-full space-y-2">
          <div className="card-shine rounded-xl p-1 flex items-center gap-2 glow-gold">
            <Search size={16} className="ml-3 shrink-0" style={{ color: "var(--gold)" }} />
            <input
              type="text"
              value={riotId}
              onChange={e => { setRiotId(e.target.value); setError(""); }}
              placeholder="GameName#TAG"
              className="flex-1 bg-transparent py-3 pr-3 outline-none text-base placeholder:opacity-30"
              autoFocus
            />
            <button type="submit" disabled={!riotId}
              className="shrink-0 px-5 py-2.5 rounded-lg text-sm font-bold transition-all disabled:opacity-30"
              style={{ background: "linear-gradient(135deg,#c89b3c,#8a6d2a)", color: "#070b14" }}>
              Analyser
            </button>
          </div>
          {error && <p className="text-xs text-center" style={{ color: "var(--red)" }}>{error}</p>}
        </form>

        {/* Feature pills */}
        <div className="flex flex-wrap justify-center gap-2">
          {[
            { icon: <TrendingUp size={13} />, label: "Win % minute par minute" },
            { icon: <Swords size={13} />, label: "Simulateur de partie" },
            { icon: <Users size={13} />, label: "Qui est le fautif ?" },
          ].map(f => (
            <span key={f.label}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs"
              style={{ background: "var(--bg-card)", border: "1px solid var(--border)", color: "var(--muted)" }}>
              <span style={{ color: "var(--gold)" }}>{f.icon}</span>{f.label}
            </span>
          ))}
        </div>

        <button onClick={() => router.push("/simulator")}
          className="text-xs opacity-50 hover:opacity-100 transition-opacity"
          style={{ color: "var(--gold)" }}>
          Essayer le simulateur sans compte →
        </button>
      </div>
    </main>
  );
}
