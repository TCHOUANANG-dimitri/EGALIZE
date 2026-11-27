# Conception d'un égaliseur audio numérique (Projet 2)

Application Streamlit : importer un fichier WAV, séparer ses graves, médiums et
aigus, régler le gain de chaque bande, puis recombiner et écouter le résultat.

**Application en ligne : https://egalize.streamlit.app/**

## Lancement

```powershell
pip install -r requirements.txt
streamlit run streamlit_app.py
```

L'application s'ouvre sur `http://localhost:8501`. Le fichier importé n'est
jamais modifié. Un fichier d'exemple est fourni dans `donnees/originales/`.

## Le parcours

| Page | Contenu |
|---|---|
| 1 · Fichier | Import, choix de l'extrait (10 à 30 s), écoute, fréquences de coupure, spectre de l'original et des trois bandes en couleurs. |
| 2 · Bandes | Pour la bande choisie : gain (−12 à +12 dB, boutons + / − ou saisie), écoute avant / après gain, spectre et forme d'onde. |
| 3 · Recombinaison | Signal reformé : écoute comparée à l'original, spectre et forme d'onde avant / après, export WAV. |

Les réglages sont conservés quand on change de page.

## Les filtres

Les bandes sont obtenues dans `egaliseur/filtres.py` avec un passe-bas par
lissage exponentiel, appliqué aller puis retour pour supprimer le retard :

```
graves  = passe_bas(x, coupure basse)
médiums = passe_bas(x, coupure haute) − passe_bas(x, coupure basse)
aigus   = x − passe_bas(x, coupure haute)
```

Les trois bandes additionnées redonnent exactement le signal d'origine (gains à
0 dB). Le filtre vaut −3 dB à chaque fréquence de coupure ; comme il est d'ordre
faible, les bandes se chevauchent près des coupures.

## Choix à connaître pour le rapport

- **Pas de normalisation cachée** : l'écoute se fait au niveau réel. Si un
  signal dépasse 0 dBFS, il est abaissé à −1 dBFS et l'application l'indique.
- **Coupures** sur la grille des tiers d'octave (ISO 266), sous la fréquence de
  Nyquist. Par défaut : 250 Hz et 4 kHz.

## Organisation du projet

```
├── streamlit_app.py       point d'entrée : thème et navigation
├── .streamlit/config.toml thème clair : blanc, bleu électrique, or
├── egaliseur/
│   ├── filtres.py         séparation en trois bandes, gains, recombinaison
│   ├── dsp_backend.py     contrat que respectent les filtres
│   ├── pipeline.py        séparer → gains → recombiner, avec vérifications
│   ├── audio_io.py        lecture WAV, extrait, spectre, écoute, export
│   ├── signal_analysis.py mesures (niveaux, coupures)
│   ├── vues/              pages : fichier, bandes, recombinaison
│   └── interface/         état partagé, navigation, graphiques, style, logo
├── tests/                 tests unitaires
├── donnees/originales/    données brutes, jamais modifiées
├── donnees/egalisees/     versions exportées
└── docs/                  sujet du projet (PDF)
```

## Tests

```powershell
python -B -m unittest -v
```
