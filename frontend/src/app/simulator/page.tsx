"use client";
import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Slider { key: string; label: string; min: number; max: number; step: number; unit?: string; }

const SLIDERS: Slider[] = [
  { key: "game_time_minutes", label: "Temps de jeu",          min: 5, max: 45, step: 1, unit: "min" },
  { key: "gold_diff",         label: "Avantage gold",         min: -15000, max: 15000, step: 100, unit: "g" },
  { key: "gold_slope",        label: "Momentum gold",         min: -1500, max: 1500, step: 50, unit: "g/min" },
  { key: "current_gold_diff", label: "Gold non dépensé",      min: -5000, max: 5000, step: 100, unit: "g" },
  { key: "level_diff",        label: "Avantage niveaux",      min: -12, max: 12, step: 1 },
  { key: "cs_diff",           label: "Avantage CS",           min: -200, max: 200, step: 5 },
  { key: "kills_diff",        label: "Avantage kills",        min: -20, max: 20, step: 1 },
  { key: "kills_last_3min",   label: "Momentum kills (3 min)", min: -10, max: 10, step: 1 },
  { key: "damage_diff",       label: "Avantage dégâts",       min: -60000, max: 60000, step: 1000, unit: "dmg" },
  { key: "players_alive_diff", label: "Joueurs vivants",      min: -5, max: 5, step: 1 },
  { key: "first_blood",       label: "First Blood",           min: -1, max: 1, step: 1 },
  { key: "towers_diff",       label: "Avantage tours",        min: -11, max: 11, step: 1 },
  { key: "plates_diff",       label: "Plaques détruites",     min: -6, max: 6, step: 1 },
  { key: "inhibitors_diff",   label: "Avantage inhibiteurs",  min: -3, max: 3, step: 1 },
  { key: "first_tower",       label: "Première tour",         min: -1, max: 1, step: 1 },
  { key: "dragons_diff",      label: "Avantage dragons",      min: -4, max: 4, step: 1 },
  { key: "dragon_soul",       label: "Dragon Soul",           min: -1, max: 1, step: 1 },
  { key: "heralds_diff",      label: "Avantage Hérauts",      min: -2, max: 2, step: 1 },
  { key: "barons_diff",       label: "Avantage barons",       min: -3, max: 3, step: 1 },
  { key: "baron_active",      label: "Buff Baron actif",      min: -1, max: 1, step: 1 },
  { key: "elder_active",      label: "Buff Elder actif",      min: -1, max: 1, step: 1 },
  { key: "void_grubs_diff",   label: "Void Grubs",            min: -6, max: 6, step: 1 },
];

const DEFAULTS: Record<string, number> = {
  game_time_minutes: 20, gold_diff: 0, gold_slope: 0, current_gold_diff: 0,
  level_diff: 0, cs_diff: 0, kills_diff: 0, kills_last_3min: 0,
  damage_diff: 0, players_alive_diff: 0, first_blood: 0,
  towers_diff: 0, plates_diff: 0, inhibitors_diff: 0, first_tower: 0,
  dragons_diff: 0, dragon_soul: 0, heralds_diff: 0, barons_diff: 0,
  baron_active: 0, elder_active: 0, void_grubs_diff: 0,
};

export default function SimulatorPage() {
  const router = useRouter();
  const [values, setValues] = useState(DEFAULTS);
  const [result, setResult] = useState<{ blue_win_probability: number; feature_impacts: Record<string, number> } | null>(null);
  const [loading, setLoading] = useState(false);

  const predict = useCallback(async (v: typeof values) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/predict`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(v),
      });
      setResult(await res.json());
    } finally { setLoading(false); }
  }, []);

  function handleChange(key: string, val: number) {
    const next = { ...values, [key]: val };
    setValues(next);
    predict(next);
  }

  const prob = result?.blue_win_probability ?? 50;
  const probColor = prob > 60 ? "var(--blue)" : prob < 40 ? "var(--red)" : "var(--gold)";

  // Top impacts triés par valeur absolue
  const impacts = result
    ? Object.entries(result.feature_impacts)
        .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
        .slice(0, 6)
    : [];

  const labelMap: Record<string, string> = {
    gold_diff: "Gold", gold_slope: "Momentum gold", current_gold_diff: "Gold pocket",
    level_diff: "Niveaux", cs_diff: "CS", kills_diff: "Kills",
    kills_last_3min: "Kills récents", damage_diff: "Dégâts",
    players_alive_diff: "Joueurs vivants", first_blood: "First Blood",
    towers_diff: "Tours", plates_diff: "Plaques", inhibitors_diff: "Inhibiteurs",
    first_tower: "1ère Tour", dragons_diff: "Dragons", dragon_soul: "Dragon Soul",
    heralds_diff: "Hérauts", barons_diff: "Barons", baron_active: "Buff Baron",
    elder_active: "Buff Elder", void_grubs_diff: "Void Grubs",
    game_time_minutes: "Temps",
  };

  return (
    <main className="min-h-screen px-6 md:px-12 lg:px-20 py-12">
      <button onClick={() => router.push("/")}
        className="flex items-center gap-2 text-sm mb-8 opacity-50 hover:opacity-100 transition-opacity"
        style={{ color: "var(--gold)" }}>
        <ArrowLeft size={14} /> Retour
      </button>

      <div className="mb-8">
        <p className="text-xs tracking-widest uppercase mb-1" style={{ color: "var(--gold-dim)" }}>Outil interactif</p>
        <h1 className="text-4xl font-black text-gold-gradient">Simulateur</h1>
        <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
          Ajustez les métriques et voyez en temps réel comment le modèle prédit l&apos;issue.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

        {/* Sliders */}
        <div className="card-shine rounded-xl p-5 space-y-5">
          {SLIDERS.map(s => (
            <div key={s.key}>
              <div className="flex justify-between text-xs mb-2">
                <span style={{ color: "var(--muted)" }}>{s.label}</span>
                <span className="font-mono font-bold" style={{ color: "var(--gold)" }}>
                  {values[s.key] > 0 ? "+" : ""}{values[s.key]}{s.unit ?? ""}
                </span>
              </div>
              <input
                type="range" min={s.min} max={s.max} step={s.step}
                value={values[s.key]}
                onChange={e => handleChange(s.key, Number(e.target.value))}
                className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                style={{
                  background: `linear-gradient(to right, var(--gold) 0%, var(--gold) ${
                    ((values[s.key] - s.min) / (s.max - s.min)) * 100
                  }%, var(--bg) ${
                    ((values[s.key] - s.min) / (s.max - s.min)) * 100
                  }%, var(--bg) 100%)`,
                  accentColor: "var(--gold)",
                }}
              />
            </div>
          ))}
        </div>

        {/* Result */}
        <div className="space-y-4">
          {/* Big probability */}
          <div className="card-shine rounded-xl p-6 text-center glow-gold">
            <p className="text-xs tracking-widest uppercase mb-3" style={{ color: "var(--muted)" }}>
              Victoire équipe bleue
            </p>
            {loading
              ? <Loader2 size={32} className="animate-spin mx-auto" style={{ color: "var(--gold)" }} />
              : (
                <div>
                  <p className="text-7xl font-black tabular-nums" style={{ color: probColor }}>
                    {prob.toFixed(1)}
                    <span className="text-3xl">%</span>
                  </p>
                  <div className="mt-4 h-2 rounded-full overflow-hidden" style={{ background: "var(--bg)" }}>
                    <div className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${prob}%`, background: probColor }} />
                  </div>
                </div>
              )
            }
          </div>

          {/* Feature impacts */}
          {impacts.length > 0 && (
            <div className="card-shine rounded-xl p-5">
              <p className="text-xs font-semibold mb-4 tracking-widest uppercase" style={{ color: "var(--muted)" }}>
                Impact sur la prédiction
              </p>
              <div className="space-y-2.5">
                {impacts.map(([feat, val]) => {
                  const isPos = val > 0;
                  const barW = Math.min(Math.abs(val) / 30 * 100, 100);
                  return (
                    <div key={feat}>
                      <div className="flex justify-between text-xs mb-1">
                        <span style={{ color: "var(--muted)" }}>{labelMap[feat] ?? feat}</span>
                        <span className="font-bold font-mono" style={{ color: isPos ? "var(--blue)" : "var(--red)" }}>
                          {isPos ? "+" : ""}{val.toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-1 rounded-full" style={{ background: "var(--bg)" }}>
                        <div className="h-full rounded-full"
                          style={{ width: `${barW}%`, background: isPos ? "var(--blue)" : "var(--red)" }} />
                      </div>
                    </div>
                  );
                })}
              </div>
              <p className="text-xs mt-4" style={{ color: "var(--muted)" }}>
                Delta de probabilité marginal par feature (SHAP)
              </p>
            </div>
          )}

          {/* Reset */}
          <button onClick={() => { setValues(DEFAULTS); setResult(null); }}
            className="w-full py-3 rounded-xl text-sm font-semibold transition-all"
            style={{ border: "1px solid var(--border)", color: "var(--muted)" }}>
            Réinitialiser
          </button>
        </div>
      </div>
    </main>
  );
}
