# Passation — PREDICT.GG (lol-predictor)

Doc de reprise pour Eliott (et son agent IA). Objectif : cloner le repo, le faire
tourner, et **re-capturer les 4 screenshots** dont la présentation a besoin. Le reste
est déjà fait.

---

## TL;DR

- Le modèle a été **refondu (v6)** : fuite de données corrigée, features réparées et
  enrichies, calibration corrigée, explications SHAP. Chiffres honnêtes ci-dessous.
- La **game de démo** est `EUW1_7892275623` (Vayne, `Roller Coaster#abouf`, victoire en
  comeback). Elle est **mise en cache** dans `data/cache/` → elle tourne **sans clé API**.
- La présentation (`~/Downloads/PREDICT-GG_Soutenance_v6.pptx`) a ses **notes** à jour.
  Il reste à mettre à jour les **chiffres dans les images** et à **re-capturer 4 écrans**
  depuis l'app v6 (section 5).

---

## 1. Ce qui a changé (v6)

| Sujet | Avant | Après (v6) |
|-------|-------|------------|
| Split train/test | aléatoire par ligne (**fuite**) | temporel groupé par `match_id` |
| AUC affichée | 0,856 (gonflée) | **0,835** (honnête) |
| Snapshots | 41 111 (5 instants/game) | **246 350** (1/minute, min 5→40) |
| Features | 30 (dont bugs/doublons) | **22** (nettoyées + enrichies) |
| `dragon_soul` | cassé (teamId=0) | dérivé du 4e dragon |
| `kills_last_3min` | bleu uniquement | vrai diff bleu − rouge |
| Momentum / late game | absent | `gold_slope`, `players_alive_diff`, `baron_active` |
| Calibration | sigmoid (ECE 0,048) | **isotonic** (ECE 0,027) |
| Explications | — | SHAP (`src/models/explain.py`) |
| Courbe win% | brute (saccadée) | lissée EMA |

L'ancien modèle et l'ancien dataset sont dans `backup_v1/` (non versionné).

## 2. Chiffres officiels (à utiliser partout : deck, app, oral)

- **AUC 0,835** (split temporel groupé, sans fuite) — jusqu'à **0,91 à la minute 25**
- **Accuracy 74,9 %** en agrégé · **Brier 0,166** · **ECE 0,027** (bien calibré)
- Baseline `gold_diff` seul = **AUC 0,821** · Modèle de draft = **AUC 0,513**
- Données : **ranked EUW, Silver → Challenger** (PAS « Master+ »)
- **22 features**, toutes des différentiels bleu − rouge
- AUC par minute : 0,76 (min 10) · 0,83 (min 15) · 0,88 (min 20) · **0,91 (min 25)** · 0,89 (min 30)

## 3. La game de démo — `EUW1_7892275623`

Vayne ADC, `Roller Coaster#abouf`, EUW, **victoire en comeback**, 37,8 min.

Courbe win% équipe bleue (lissée, modèle v6) :

```
min  5 : 61 %      min 15 : 33 %      min 20 : 15 %  ← gel de la démo (−10 074 or)
min 21 : 13 %  (creux)                min 32 : 26 %  (baron → bascule)
min 35 : >50 %                        min 38 : 67 %  → VICTOIRE
```

État exact à la minute 20 (pour la slide 20) : or **−10 074**, kills **−12**, tours **−6**,
dragons **+2**, un joueur de moins. Le modèle donne l'équipe bleue à **~15 %** → elle gagne
quand même. Récit assumé : « une proba est un instantané, pas une fatalité ».

## 4. Lancer le projet

```bash
# 1. Backend Python
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Frontend
cd frontend && npm install && cd ..

# 3. Tout lancer (API :8000 + front Next en prod :3000)
bash run_demo.sh            # --build pour reconstruire le front

# App Streamlit pédagogique (pipeline ML + SHAP), séparément :
streamlit run streamlit_explain.py     # :8501
```

**Clé API Riot** (`.env`, `RIOT_API_KEY`) : nécessaire seulement pour chercher de
**nouveaux** joueurs/games (les clés dev expirent toutes les 24 h). La game de démo
`EUW1_7892275623` est **en cache** → elle marche sans clé. Copier `.env.example` → `.env`
et y mettre une clé fraîche depuis developer.riotgames.com si besoin d'autres games.

> Piège réseau école : le FortiGate bloque `api.riotgames.com` → partager la 4G du tel.

## 5. Re-capturer les 4 screenshots (LE todo principal)

Lancer l'app (section 4), puis :

| Slide | Quoi | Où / comment |
|-------|------|--------------|
| **22** | La courbe **comeback** de Game A | `http://localhost:3000/game/EUW1_7892275623` → capturer le graphe win% (creux ~13 % min 21 → remontée min 32 → victoire 67 %). Remplace l'ancienne image d'une game perdue. |
| **20** | L'**état de la partie à la min 20** | même page `/game/EUW1_7892275623`, lire/capturer les écarts à la minute 20 (or −10 074, kills −12, tours −6, dragons +2). |
| **16** | Le **simulateur SHAP** | `http://localhost:3000/simulator` → régler une avance bleue (ex. gold +5000, dragons +2, niveaux +5) → capturer la jauge (~91 %) + les impacts SHAP par variable. |
| **15** | Une **courbe d'une game pliée tôt** | `/game/<un_match_id_de_stomp>` (une game gagnée nettement) pour illustrer « parfois c'est décidé tôt ». Si pas d'autre game en cache, pull une game via une clé API valide. |

Les chiffres à corriger DANS les images (non re-capturables) sont listés dans les **notes**
du pptx v6 (préfixe `[IMAGE À METTRE À JOUR : …]`) et dans le prompt design fourni à part.

## 6. Reproduire / réentraîner

```bash
source venv/bin/activate
PYTHONPATH=. python -m src.data.parse_timelines   # raw → data/processed/features.parquet
PYTHONPATH=. python -m src.models.train --tune     # retune + entraîne + métriques
# métriques → docs/results/run_*.json ; modèle → models/xgboost_final.pkl (+ model_meta.json)
```

`data/raw/` (8,6 Go de timelines Riot) n'est **pas** versionné. Sans lui, impossible de
re-parser — mais le `features.parquet`, le modèle et le cache de démo sont versionnés,
donc l'app tourne sans re-parser.

## 7. Fichiers clés (pour un agent qui reprend)

- `src/features/build_features.py` — **contrat de features** (les 22, + helpers respawn). Source de vérité.
- `src/data/parse_timelines.py` — raw Riot → features (entraînement).
- `src/data/fetch_player.py` — mêmes features servies live (`extract_full_timeline`). **Doit rester en parité** avec parse_timelines.
- `src/models/train.py` — split temporel groupé, CV groupée, Brier/ECE/par-minute, calibration isotonic, versioning (`model_meta.json`).
- `src/models/predict.py` — inférence (reindex robuste) + lissage EMA (`smooth_probabilities`).
- `src/models/explain.py` — SHAP par prédiction.
- `api/main.py` — FastAPI (`/predict`, `/game/{id}`, `/pro/...`), schéma `FeatureInput` (22 champs).
- `frontend/src/app/simulator/page.tsx` — sliders du simulateur (22 features).
- `streamlit_explain.py` — walkthrough ML pédagogique.

## 8. Limites connues / chemins dégradés

- **Esports** (`src/data/fetch_esports.py`) : ne fournit qu'une partie des 22 features
  (le reste → 0 via reindex). Prédictions de tournoi dégradées, mais pas de crash.
- **Live Client** (`src/live/live_client.py`) : l'or est **estimé** (l'API live ne donne pas
  le gold total) et beaucoup de features ne sont pas disponibles en live (→ 0). Sert à la
  démo live `app/main.py`, qui nécessite une vraie partie LoL en cours.

## 9. État de la présentation

- `~/Downloads/PREDICT-GG_Soutenance_v6.pptx` : **notes** à jour (récit comeback, chiffres v6,
  Silver→Challenger, `[À REMPLIR]` remplis). Original sauvegardé en `_ORIGINAL_backup.pptx`.
- Reste : corriger les **chiffres dans les images** (les slides sont des images, pas du texte
  éditable) + re-capturer les 4 écrans de la section 5.
