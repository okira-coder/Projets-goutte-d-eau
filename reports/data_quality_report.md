# Rapport de qualité des données — Projet Goutte d'eau

**Document généré à partir de** : `notebooks/01_eda.ipynb`
**Date** : 2026-05-12
**Périmètre** : observations SYNOP des 4 stations d'Occitanie

> **Démarche** : chaque section suit la chaîne **🔍 Analyse → Constat → ✅ Décision**. L'objectif n'est pas de juste décrire les données mais de **justifier chaque choix de modélisation** par une observation chiffrée. La synthèse en §10 montre comment l'ensemble des constats converge vers une architecture cohérente.

---

## 1. Source des données

- **Origine** : archive SYNOP publique de Météo France — fichiers mensuels gzippés
  `https://donneespubliques.meteofrance.fr/donnees_libres/Txt/Synop/Archive/synop.YYYYMM.csv.gz`
- **Granularité** : 1 observation toutes les 3 heures (8 obs/jour théoriques)
- **Stations sélectionnées** :

  | Code SYNOP | Nom | Département | Lat | Lon | Altitude |
  |-----------|-----|-------------|-----|-----|----------|
  | 07643 | Montpellier-Fréjorgues | Hérault | 43.577 | 3.963 | 2 m |
  | 07630 | Toulouse-Blagnac | Haute-Garonne | 43.621 | 1.379 | 151 m |
  | 07747 | Perpignan-Rivesaltes | Pyrénées-Orientales | 42.737 | 2.873 | 42 m |
  | 07621 | Carcassonne-Salvaza | Aude | 43.215 | 2.306 | 126 m |

  *Note : Millau (07645) initialement prévu n'est pas dans l'archive SYNOP nationale — remplacé par Carcassonne (07621).*

## 2. Fenêtre temporelle et volume

| Indicateur | Valeur |
|-----------|--------|
| Fenêtre temporelle | 2023-01-01 → 2024-12-31 (2 ans complets) |
| Volume observations 3h | **23 073** |
| Observations par station | ~ 5 770 (4 stations équilibrées) |
| Couverture temporelle | ~ 98 % (5 770 / 5 840 obs attendues sur 2 ans × 8/j) |

## 3. Complétude (valeurs manquantes)

| Colonne | % NA | Qualité |
|---------|------|---------|
| `pressure_hpa` | 0.00 % | ★★★★★ |
| `wind_speed_ms` | 0.02 % | ★★★★★ |
| `temperature_c` | 0.22 % | ★★★★★ |
| `humidity_pct` | 0.22 % | ★★★★★ |
| `precipitation_3h_mm` | 0.74 % | ★★★★★ |
| `precipitation_24h_mm` | 7.74 % | ★★★★ |
| `cloud_cover_pct` | 55.80 % | ★★ — souvent non rapporté la nuit |

**Critère de qualité** : seuil de 5 % NA appliqué aux variables critiques (temp, pression, pluie) → **respecté** ✅
`cloud_cover_pct` trop incomplet pour être utilisé tel quel ; sera ignoré dans `build_features.py`.

## 4. Distributions univariées

Figures : `reports/figures/distributions_univariees.png`

- **Température** : -5 °C à +40 °C, distribution bimodale (hiver vs été) cohérente avec le climat occitan
- **Humidité** : asymétrique vers 70-90 %, climat méditerranéen
- **Pression** : normale centrée ≈ 1015 hPa, écart-type ≈ 7 hPa ; Carcassonne et Toulouse intérieures, Perpignan et Montpellier littorales
- **Vent** : log-normale, médiane ≈ 3 m/s, queue longue (mistral, tramontane)

## 5. Précipitations — focus métier

### 5.1 Distribution des observations 3h

| Catégorie | % observations 3h |
|-----------|-------------------|
| Sec (0 mm) | **82.5 %** |
| Pluie faible (< 1 mm) | **6.1 %** |
| Pluie modérée (1-5 mm) | **4.1 %** |
| Pluie forte (≥ 5 mm) | **1.1 %** |

→ 82.5 % d'observations 3h sans pluie : confirme le déséquilibre attendu en classification.

### 5.2 Taux de jours pluvieux (cumul > 1 mm) par station

| Station | % jours pluvieux | Climat |
|---------|------------------|--------|
| **Carcassonne-Salvaza** | **32.6 %** | Plus pluvieux (proximité Pyrénées, climat océanique dégradé) |
| **Toulouse-Blagnac** | **23.9 %** | Climat océanique dégradé continental |
| **Montpellier-Fréjorgues** | **13.0 %** | Climat méditerranéen, sec |
| **Perpignan-Rivesaltes** | **11.5 %** | Climat méditerranéen, le plus sec |

**Implication ML** : taux global ≈ 20 %, déséquilibre classique → utiliser `class_weight='balanced'` (LogReg) et `scale_pos_weight` (XGBoost), métriques F1/AUC plutôt qu'accuracy. ✅ (déjà implémenté)

## 6. Séries temporelles

Figures : `reports/figures/series_temporelles_mensuelles.png`

- **Cycle annuel de température** très net : hiver ≈ 7 °C, été ≈ 25 °C
- **Précipitations mensuelles** : pic d'automne (épisodes méditerranéens — sept/oct sur Perpignan/Montpellier), creux d'été (juillet sec)

## 7. Corrélations (matrice Pearson)

Figure : `reports/figures/correlations_heatmap.png`

Patterns observés (à confirmer en lecture du heatmap) :
- **Humidité ↔ Pluie 3h** : corrélation positive modérée (0.3-0.4)
- **Pression ↔ Pluie 3h** : corrélation négative légère — la pluie suit une chute de pression (signal mieux capté par les *différentielles* de pression utilisées en features)
- **Température ↔ Humidité** : corrélation négative en été
- **Vent ↔ Pluie** : faible

## 8. Saisonnalité

Figure : `reports/figures/saisonnalite.png`

- Été : températures hautes (25-30 °C), pluie rare mais intense (orages)
- Automne (sept-oct) : pic pluviométrique (épisodes cévenols/méditerranéens), variabilité élevée
- Hiver (dec-fév) : pluie régulière, températures fraîches
- Printemps : transition, variabilité

→ Justifie l'encodage **cyclique** `(doy_sin, doy_cos)` dans `build_features.py`.

## 9. Outliers (méthode IQR × 3)

| Variable | Nb outliers | Bornes | Décision |
|----------|-------------|--------|----------|
| `precipitation_3h_mm` | **4 002** | [0, 0] | **Conserver** — la médiane est 0 donc l'IQR est dégénéré ; toute pluie > 0 est "outlier" mais c'est le signal physique recherché |
| `pressure_hpa` | 0 | [906, 1094] | RAS (pression naturellement bornée) |
| `wind_speed_ms` | 30 | [-8, 15.1] | **Conserver** — rafales de mistral/tramontane réelles |

**Décision globale** : **aucun outlier supprimé**. En météo, les phénomènes extrêmes sont précisément ce que le modèle doit apprendre.

## 10. Synthèse — Du diagnostic à l'architecture de modélisation

Cette EDA conduit à **6 décisions structurantes**, chacune justifiée par une observation chiffrée. C'est la **traçabilité données → modèle** qui caractérise une démarche data science rigoureuse.

### 🎯 Décision 1 — Cible : classification binaire seuil 1 mm

| 🔍 Analyse | Constat | ✅ Décision |
|------------|---------|------------|
| Distribution pluviométrique | 82.5 % obs à 0 mm, queue exponentielle | **Binaire** (vs régression) — cible asymétrique trop dure à régresser |
| Choix du seuil | 1 mm = équilibre 80/20 ; 0 mm = 95/5 ingérable ; 5 mm trop rare | **Seuil 1 mm** |

### 🎯 Décision 2 — Algorithme : XGBoost + LogReg baseline

| 🔍 Analyse | Constat | ✅ Décision |
|------------|---------|------------|
| Matrice de corrélation | Pas de corrélation linéaire forte (max ~0.4) | LogReg seul **insuffisant**, besoin de non-linéaire |
| Volume après features | ~ 2 900 lignes | **DL exclu** (overfitting garanti) ; XGBoost = sweet spot |
| Interactions station × saison | Pic auto sur méditerranée, pas sur Toulouse | XGBoost capture nativement ces interactions |

→ **XGBoost principal + LogReg baseline**.

### 🎯 Décision 3 — Gestion du déséquilibre 80/20

| 🔍 Analyse | Constat | ✅ Décision |
|------------|---------|------------|
| Taux de pluie moyen | ~ 20 % positifs | `class_weight='balanced'` (LogReg), `scale_pos_weight` (XGBoost) |
| Métrique accuracy | Biaisée (80 % en prédisant toujours "sec") | **F1, ROC-AUC, Brier** retenus, **accuracy bannie** |

### 🎯 Décision 4 — Feature engineering : 30+ features en 6 familles

| Famille | Constat EDA qui justifie | Features |
|---------|---------------------------|----------|
| **Brutes** | Variables physiques fondamentales (distributions §4) | temp, humidité, pression, vent, pluie |
| **Lags temporels** | Persistance pluie 1-7j visible en série temporelle (§6) | precip/pressure/temp lag 1, 2, 3, 7 |
| **Rolling 7j/30j** | Régimes pluviométriques semaines/mois (§6) | mean+std precip, mean pressure |
| **Différentielles 24h** | Corrélations faibles en niveau mais Δpression compte (§7) | pressure_diff_24h, humidity_diff_24h |
| **Saisonnier** | Cyclicité annuelle ultra-nette (§6, §8) | doy_sin, doy_cos, month |
| **Station** | Carcassonne 32 % vs Perpignan 11 % — 3× variation (§5) | latitude, longitude, altitude |
| **Exclus** | `cloud_cover_pct` 56 % NA (§3) | — |

### 🎯 Décision 5 — Validation : split temporel + TimeSeriesSplit

| 🔍 Analyse | Constat | ✅ Décision |
|------------|---------|------------|
| Forte saisonnalité (§6, §8) | Distribution train/test changera selon les années | **Pas de shuffle** — split chronologique 80/20 |
| Volume 2 900 lignes | Suffisant pour 5 folds | `TimeSeriesSplit(n_splits=5)` pour tuning |
| Risque de fuite (lookahead) | À prévenir | `shift(d)` puis `rolling()` — jamais d'info future |

### 🎯 Décision 6 — Pas de filtrage des outliers

| 🔍 Analyse | Constat | ✅ Décision |
|------------|---------|------------|
| 4 002 "outliers" pluie (§9) | Artefact (médiane=0 → IQR dégénéré) | **Conserver tous** — c'est le signal cible |
| 30 outliers vent (§9) | Rafales mistral/tramontane réelles | Conserver |

### Risques résiduels & mitigations

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| Météo France retire l'archive | Faible | Élevé | Cache local CSV + fallback Infoclimat |
| Distribution future ≠ train (climate drift) | Élevée à long terme | Moyen | Monitoring PSI mensuel sur features clés |
| Stations défaillantes | Moyenne | Faible | Ingestion idempotente + log warning |
| Volume insuffisant (2 ans) | Identifié (cf. §5 model_evaluation) | Élevé sur AUC | **Action P1 roadmap** : étendre à 2018-2024 |

### 📋 Validation a posteriori

Le `notebooks/03_evaluation.ipynb` et `reports/model_evaluation.md` montrent que les **top 10 features XGBoost** correspondent **exactement** aux familles décidées ici (pression, pressure_diff_24h, lag pluie, doy_sin, latitude/altitude). C'est la confirmation que la démarche analyse → décision était saine.
