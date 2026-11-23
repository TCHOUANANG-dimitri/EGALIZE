# EGALIZE — égaliseur audio numérique (Projet 2)

Application Streamlit pédagogique pour le projet 2 du module de traitement du
signal : importer une piste WAV, relever ses caractéristiques, choisir un
extrait de 10 à 30 s, analyser sa forme d'onde et son spectre, puis préparer
une égalisation à trois bandes (graves, médiums, aigus).

## Installation et lancement

```powershell
pip install -r requirements.txt
streamlit run streamlit_app.py
```

L'application s'ouvre dans le navigateur (par défaut sur `http://localhost:8501`).
Le fichier importé reste sur l'ordinateur et n'est jamais modifié : tout le
travail se fait sur une copie en mémoire.

Pas de fichier sous la main ? Le bouton **Utiliser Techno_music_001.wav** charge
la piste d'exemple rangée dans `donnees/originales/`.

## Le parcours : une page par étape

La barre latérale (bleu électrique) liste les cinq étapes. Une coche indique
une étape faite, un cadenas une étape qui attend les filtres. Chaque page se
termine par des boutons « Précédent / Suivant », et un bandeau rappelle la piste,
l'extrait, les coupures et les gains en cours. Les réglages sont conservés quand
on change de page.

| Page | Ce que l'on fait | État |
|---|---|---|
| 1 · Piste | Import WAV mono/stéréo ; fréquence d'échantillonnage, canaux, durée, résolution, nombre d'échantillons et fréquence de Nyquist relevés automatiquement. | ✅ |
| 2 · Extrait | Vue d'ensemble du fichier, sélection de 10 à 30 s, écoute au niveau réel, forme d'onde de l'extrait. | ✅ |
| 3 · Fréquences | Spectre (méthode de Welch, axe logarithmique), fréquences de coupure à deux poignées, part de l'énergie dans chaque zone. | ✅ |
| 4 · Égaliseur | Gain de −12 à +12 dB par bande, préréglages, gabarit visé, estimation du risque d'écrêtage. | ✅ (réglages) |
| 5 · Résultat | Écoute avant/après et par bande, spectres comparés, export WAV/FLAC/MP3, versions enregistrées (CSV). | 🔒 en attente des filtres |

La barre latérale affiche aussi l'état du moteur de filtrage et une liste de
contrôle du cahier des charges du projet 2.

## Ce qui reste à faire : les filtres

Les filtres ne sont volontairement pas implémentés : ils seront écrits par le
groupe une fois les notions comprises, en commençant par le passe-bas. Tant
qu'ils ne sont pas branchés, l'application analyse le signal sans le modifier,
et le signale clairement.

Tout se passe dans **`egaliseur/filtres.py`**. Il faudra y écrire une classe qui
respecte le contrat de `egaliseur/dsp_backend.py`, puis remplacer
`BACKEND = None` par `BACKEND = VotreClasse()` :

1. `split_bands(samples, sample_rate, low_cutoff_hz, high_cutoff_hz)` — renvoie
   les trois signaux `bass` (passe-bas), `mid` (passe-bande) et `treble`
   (passe-haut), de même forme que l'extrait ;
2. `apply_gains(bands, gains_db)` — applique le gain de chaque bande ;
3. `recombine_bands(bands)` — additionne les bandes pour obtenir le signal final.

La page 5 s'active alors automatiquement : écoute de chaque bande, écoute du
mix, spectre de chaque bande (utile pour observer la pente réelle des filtres),
comparaison des spectres avant/après et export. Les résultats renvoyés sont
vérifiés (présence des trois bandes, forme, valeurs finies) dans
`egaliseur/pipeline.py`. Une modification de `filtres.py` est prise en compte
sans redémarrer l'application.

## Choix à connaître pour le rapport

- **Aucune normalisation cachée.** Le lecteur audio de Streamlit normalise
  normalement les signaux ; l'application lui fournit des octets WAV au niveau
  réel, pour que l'écoute avant/après soit honnête.
- **Écrêtage surveillé.** La crête de l'extrait (en dBFS) est affichée, avec une
  estimation du risque d'écrêtage selon les gains choisis. Une fois les filtres
  branchés, la crête réelle du mix est mesurée ; si elle dépasse 0 dBFS, le
  niveau peut être abaissé automatiquement (crête ramenée à −1 dBFS).
  L'abaissement appliqué est affiché et enregistré avec la version, comme le
  demande le sujet. L'export est refusé si le signal écrête.
- **Fréquences de coupure normalisées.** Les valeurs proposées suivent la grille
  des tiers d'octave (ISO 266 : …, 200, 250, 315, …, 3150, 4000, 5000 Hz…),
  toujours sous la fréquence de Nyquist. Par défaut : 250 Hz et 4 kHz.
- **Versions.** Chaque réglage (extrait, coupures, gains, abaissement éventuel)
  peut être enregistré puis téléchargé en CSV, pour les deux versions égalisées
  demandées dans les livrables.
- **Graphiques.** Chaque graphique a un titre, des axes nommés avec unités et
  une légende ; l'icône d'appareil photo de Plotly les exporte en PNG.

## Organisation du projet

```
├── streamlit_app.py          point d'entrée : thème, navigation, barre latérale
├── requirements.txt
├── .streamlit/config.toml    thème clair : blanc, bleu électrique, or
├── egaliseur/                code du projet
│   ├── filtres.py            ← les filtres à écrire (BACKEND)
│   ├── dsp_backend.py        contrat que les filtres doivent respecter
│   ├── pipeline.py           séparer → gains → recombiner, avec vérifications
│   ├── audio_io.py           lecture WAV, extrait, spectre, écoute, export
│   ├── signal_analysis.py    mesures sans filtrage (niveaux, énergie, coupures)
│   ├── vues/                 une page par étape : piste, extrait, frequences,
│   │                         reglage, resultat
│   └── interface/            état partagé, navigation, graphiques, style, logo
├── tests/                    tests unitaires
├── donnees/
│   ├── originales/           données brutes (Techno_music_001.wav), jamais modifiées
│   └── egalisees/            versions égalisées exportées
└── docs/                     sujet du projet (PDF)
```

## Tests

```powershell
python -B -m unittest -v
```
