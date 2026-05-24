# Documentation — LoL Win Predictor

Journal de bord du projet pour préparer l'oral.

## Structure

```
docs/
├── progress/          ← journal de sessions (une par session de travail)
│   └── session_001_2026-05-24.md
├── results/           ← métriques JSON exportées automatiquement à chaque training run
├── screenshots/       ← captures d'écran manuelles (app, terminal, notebooks)
├── presentation/      ← plan de l'oral + slides
│   └── plan_oral.md
└── installation.md    ← manuel d'installation
```

## Workflow documentation

**Après chaque session de travail :**
1. Créer `docs/progress/session_NNN_YYYY-MM-DD.md` avec ce qui a été fait
2. Mettre à jour les métriques dans `plan_oral.md` si un training a tourné
3. Ajouter les screenshots dans `docs/screenshots/`

**Pour capturer un output terminal :**
```bash
python src/models/train.py 2>&1 | python docs/log_session.py "nom_du_run"
```

**Les graphiques de training** sont auto-sauvegardés dans `models/evaluation.png`.

## Sessions

| # | Date | Contenu |
|---|------|---------|
| 001 | 2026-05-24 | Setup pipeline complet, 11 features, architecture Streamlit |
