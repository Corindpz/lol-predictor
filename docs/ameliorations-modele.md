# Améliorations de précision — Blame, Winrate in-game, Draft

> Source principale : l'objet `challenges` de match-v5 (129 champs, **déjà présents dans nos JSON en cache**, zéro appel API supplémentaire) + les positions x/y minute par minute de la timeline.

---

## 1. « Qui est le fautif » — corriger le biais support-wards

### Le problème actuel
`impact = KP×0.5 + (wards×1.5 + wardsKilled×2)×0.3 − morts×3`
→ un support qui spam des wards sans mourir devient MVP même avec zéro impact réel.

### 1.1 Champs `challenges` à intégrer (déjà dans nos données)

**Mécanique / skill :**
| Champ | Ce que ça mesure |
|---|---|
| `skillshotsHit` | sorts touchés |
| `skillshotsDodged` / `dodgeSkillShotsSmallWindow` | esquives (réaction) |
| `landSkillShotsEarlyGame` | skillshots touchés en early |
| `enemyChampionImmobilizations` | CC appliqués aux champions |
| `knockEnemyIntoTeamAndKill` | hooks/déplacements convertis en kill (**Blitzcrank**) |
| `immobilizeAndKillWithAlly` / `pickKillWithAlly` | picks coordonnés |
| `soloKills` / `outnumberedKills` | kills en 1v1 / en infériorité |
| `multiKillOneSpell`, `quickSoloKills` | outplays |

**Protection / sustain (enchanteurs) :**
| Champ | Ce que ça mesure |
|---|---|
| `effectiveHealAndShielding` | heal + shield **effectif** (l'overheal ne compte pas) |
| `saveAllyFromDeath` | sauvetages avérés |
| `survivedSingleDigitHpCount`, `tookLargeDamageSurvived` | survies limites |

**Tanking / frontline :**
| Champ | Ce que ça mesure |
|---|---|
| `damageTakenOnTeamPercentage` | % des dégâts de l'équipe encaissés |
| `damageSelfMitigated` (participants) | dégâts mitigés (armure, shields propres) |
| `killedChampTookFullTeamDamageSurvived` | engage qui survit |

**Part de contribution (normalisées d'office) :**
| Champ | Ce que ça mesure |
|---|---|
| `teamDamagePercentage` | % des dégâts de l'équipe |
| `killParticipation` | KP officiel |
| `damagePerMinute`, `goldPerMinute` | efficacité |
| `bountyGold` | gold généré par les shutdowns |

**Vision *qualitative* (vs juste compter les wards) :**
| Champ | Ce que ça mesure |
|---|---|
| `visionScoreAdvantageLaneOpponent` | vision relative au vis-à-vis |
| `wardTakedowns`, `wardsGuarded` | dénying / défense de vision |
| `controlWardsPlaced`, `stealthWardsPlaced` | type de wards |
| `visionScorePerMinute` | normalisé par durée |

**Laning (proxy de la « pressure ») :**
| Champ | Ce que ça mesure |
|---|---|
| `laningPhaseGoldExpAdvantage` / `earlyLaningPhaseGoldExpAdvantage` | qui a gagné sa lane |
| `maxCsAdvantageOnLaneOpponent`, `maxLevelLeadLaneOpponent` | avance max sur le vis-à-vis |
| `turretPlatesTaken`, `kTurretsDestroyedBeforePlatesFall` | conversion de la pressure |
| `laneMinionsFirst10Minutes` | CS early |

**Macro / rotations (proxy des « rotations map ») :**
| Champ | Ce que ça mesure |
|---|---|
| `teleportTakedowns` | rotations TP converties |
| `getTakedownsInAllLanesEarlyJungleAsLaner` | roaming early |
| `killsOnLanersEarlyJungleAsJungler`, `junglerKillsEarlyJungle` | ganks |
| `enemyJungleMonsterKills`, `moreEnemyJungleThanOpponent` | invades / counter-jungle |
| `epicMonsterSteals`, `objectivesStolen` | steals |
| `dragonTakedowns`, `baronTakedowns`, `riftHeraldTakedowns`, `voidMonsterKill` | présence aux objectifs |
| `scuttleCrabKills`, `buffsStolen` | contrôle de la rivière |

**Champs `participants[]` directs (hors challenges) :**
- `totalHealsOnTeammates`, `totalDamageShieldedOnTeammates` (bruts, en complément de l'effectif)
- `timeCCingOthers`, `totalTimeCCDealt`
- `damageDealtToObjectives`, `damageDealtToTurrets`
- `totalTimeSpentDead` (le vrai coût des morts), `longestTimeSpentLiving`
- `objectivesStolen`, `largestKillingSpree`
- `spell1Casts`…`spell4Casts` (activité)

### 1.2 Timeline (déjà téléchargée pour la courbe win%)

**Coût causal d'une mort — basé sur les événements qui suivent, pas sur le timing :**
Chaque event `CHAMPION_KILL` de la timeline contient : `bounty`, `shutdownBounty`, `victimDamageDealt`, `victimDamageReceived`, `position`, `assistingParticipantIds`.
Pour chaque mort, regarder une fenêtre de ~90 s après :
- **Objectif concédé derrière** : `ELITE_MONSTER_KILL` (Nashor, dragon, herald) ou `BUILDING_KILL` par l'équipe adverse dans la fenêtre → la mort a un coût objectif. Mort solo près du pit juste avant un Nashor ennemi = malus maximal.
- **Shutdown donné pour rien** : `shutdownBounty > 0` sur sa propre mort, sans kill/objectif gagné par son équipe dans la fenêtre.
- **Mort gratuite vs trade** : `victimDamageDealt` faible = mort sans rien donner ; élevé = au moins un trade. Une mort solo (pas d'`assistingParticipantIds` côté killer) sans dégâts infligés et suivie d'un objectif perdu = la pire mort possible.
- **Mort utile** : si l'équipe gagne un objectif/des kills pendant ou juste après (sacrifice, dive trade), pas de malus.

Autres usages timeline :
- **Positions x/y par minute** (`participantFrames.position`) : temps passé hors de sa lane = proxy direct des rotations ; présence rivière/jungle ennemie.
- **Delta de win% causé par chaque mort** : on a déjà le modèle minute par minute → attribuer à chaque joueur la chute de probabilité consécutive à ses morts. Se combine avec le coût causal ci-dessus (le delta win% capture déjà implicitement le contexte objectif).

### 1.3 La clé : normalisation par rôle ET par champion
Le vrai fix du biais support :
1. **Z-score par rôle** (`teamPosition`) : un support est comparé à la distribution des supports du dataset Master+, pas aux ADC. Les wards d'un support deviennent « normales », plus un boost.
2. **Profil par champion** : sur le dataset, calculer la distribution de chaque stat **par champion**. Blitzcrank est alors jugé sur `knockEnemyIntoTeamAndKill` / `skillshotsHit` / `enemyChampionImmobilizations` (où il doit performer) et pas pénalisé sur `effectiveHealAndShielding` (où sa baseline est 0). Janna : l'inverse.
   - Alternative légère : classes de champions via les tags Data Dragon (Enchanter/Engage/Mage/Tank…) si la granularité par champion manque de données.

   **« Pourquoi ce winrate » — profil discriminant par champion (calculable depuis notre propre dataset) :**
   Pour chaque champion, séparer ses parties gagnées vs perdues, et mesurer quelles stats discriminent le plus la victoire (taille d'effet type Cohen's d, ou AUC par stat, ou coefficients d'une régression logistique par champion) :
   - Katarina → `damagePerMinute`, `teamDamagePercentage`, multikills ressortiront
   - Milio → `effectiveHealAndShielding`, `saveAllyFromDeath`
   - Blitzcrank → `knockEnemyIntoTeamAndKill`, `pickKillWithAlly`
   Le score de blame pondère alors chaque stat par son pouvoir discriminant **pour ce champion précis** : un joueur est bon s'il excelle là où les versions gagnantes de son champion excellent.
   - **Problème de volume** : ~170 champions × stats fiables = il faut beaucoup de parties par champion. Solutions : (a) collecter en continu (le fetcher tourne la nuit), (b) *partial pooling* — le profil d'un champion peu joué est tiré vers le profil moyen de sa classe, (c) ne profiler finement que les ~40 champions les plus joués, classe pour les autres.
   - **Sources externes (winrates publics)** : u.gg / lolalytics / op.gg n'ont **pas d'API publique officielle** — scraping fragile et contraire aux ToS. De toute façon ils ne fournissent que le winrate global, pas le « pourquoi » par stat. Notre dataset Master+ est la seule source qui permet le profil discriminant, et c'est plus défendable en soutenance (méthodo maîtrisée de bout en bout).
3. **Pondérer la vision par son utilité** : `visionScoreAdvantageLaneOpponent` et `wardTakedowns` plutôt que le compte brut de wards.

---

## 2. Winrate in-game — nouvelles features de snapshot

### 2.1 État du jeu plus fin
- **Joueurs vivants à l'instant t** (diff) — un 4v5 à 35 min ≈ partie décidée ; les death timers late game changent tout.
- **Buff Baron / Elder actif** + temps restant (on a `elder_active`, ajouter `baron_active` + durées).
- **Timers d'objectifs** : prochain dragon/baron dans X secondes (état des stacks → qui peut prendre le soul point).
- **Inhibiteurs respawn timers** (pas juste le compte).
- **Soul point** (3 drakes vs 1) en plus de `dragon_soul`.

### 2.2 Features de composition (gros gain attendu)
- **Scaling de la compo** : score early/mid/late par champion (courbes de winrate par tranche de durée, calculables depuis notre dataset). Interaction cruciale : être à −3k gold à 20 min avec une compo late ≠ même retard avec une compo early.
- **Répartition du gold dans l'équipe** : gold concentré sur le carry vs étalé (Gini du gold).
- **Items complétés** (diff de valeur d'items) — raffinerait `powerspike_diff`.
- **Spikes de niveau** : nombre de joueurs 6/11/16 par équipe.

### 2.3 Momentum
- **Pente du gold_diff sur les 3-5 dernières minutes** (on a `kills_last_3min`, généraliser : `gold_slope`, `objective_momentum`).
- **Diff de vision active** (wards posées − détruites sur les 3 dernières minutes, via events timeline).

### 2.4 Côté modèle
- Modèles **séparés par phase de jeu** (early <14 min / mid / late >28 min) — les features n'ont pas le même poids.
- Plus de matchs, filtrés sur un même patch (le meta shift bruite l'entraînement).
- LightGBM/CatBoost en ensemble avec XGBoost ; tuning Optuna.
- Side bleu/rouge comme feature (winrate structurellement asymétrique).

---

## 3. Draft — au-delà des paires de synergie

### 3.1 Données
- **Matrice de matchups** : winrate champion vs champion **au même poste** (Ahri vs Zed mid), pas seulement les synergies alliées.
- **Priors par champion** : winrate/pickrate global du patch, avec lissage bayésien (une paire vue 8 fois ne doit pas peser comme une paire vue 800 fois — actuellement seuil brut à 10 games).
- **Winrate par side** (bleu/rouge).

### 3.2 Features de composition d'équipe
- **Balance AD/AP** (une compo full AD se fait stack armure).
- **Frontline** : nombre de tanks/bruisers.
- **Score d'engage / disengage** (par tags ou par stats CC du dataset).
- **Courbes de scaling** agrégées (compo early vs late → prédire *quand* l'équipe doit gagner).
- **Waveclear / siege** (dégâts aux tourelles par champion dans le dataset).
- **CC total** (somme des `enemyChampionImmobilizations` moyens par champion).

### 3.3 Côté modèle
- **Embeddings de champions** : factorisation de matrice ou petit réseau entraîné sur les issues de matchs → règle le problème de sparsité des paires (deux champions jamais vus ensemble ont quand même une représentation). C'est LE saut qualitatif vs les winrates de paires bruts.
- Le modèle apprend alors synergie + counter + meta simultanément au lieu de la formule additive actuelle.

---

## 4. Ce qui reste non mesurable (et les meilleurs proxys)

| Non mesurable | Meilleur proxy disponible |
|---|---|
| Pressure en lane | `laningPhaseGoldExpAdvantage`, plates, `maxCsAdvantageOnLaneOpponent` |
| Rotations / map awareness | positions x/y timeline, `teleportTakedowns`, roaming challenges |
| Shotcalling / comms | rien — assumé dans les limites du modèle |
| Tilt / mental | streaks (déjà fait côté front) |
| Wave management | indirectement via CS diff par minute (timeline) |

---

## Ordre d'implémentation conseillé
1. **Blame v2** : challenges + z-score par rôle (1 session, gros gain visible en démo)
2. **Blame v3** : delta de win% par mort (réutilise le modèle existant — très vendeur en soutenance)
3. **Snapshot features** : joueurs vivants, baron actif, scaling de compo
4. **Draft embeddings** (le plus long, mais différenciant)
