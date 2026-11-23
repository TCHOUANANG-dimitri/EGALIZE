# Onde — égaliseur audio numérique

Interface web pédagogique pour le projet 2 : importer une piste WAV, lire ses
caractéristiques, analyser le spectre et préparer les réglages d'un égaliseur
à trois bandes.

## Ouvrir l'interface

Ouvrir `index.html` dans un navigateur moderne, ou lancer un serveur local à la
racine du dossier :

```powershell
python -m http.server 8000
```

Puis visiter `http://localhost:8000`. L'application utilise les API audio du
navigateur ; le fichier choisi reste local et n'est envoyé à aucun serveur.

## Fonctions de l'interface

- Import WAV mono/stéréo et lecture des métadonnées de l'en-tête (fréquence
  d'échantillonnage, canaux et profondeur en bits).
- Sélection et écoute d'un extrait de 10 à 30 secondes.
- Spectre FFT interactif, avec axe fréquentiel logarithmique et séparation
  visuelle des trois bandes.
- Fréquences de coupure modifiables, avec validation vis-à-vis de Nyquist.
- Commandes de gain par pas de 1 dB, limitées à ±12 dB.
- Mise en page adaptative avec une palette bleu électrique et or.

## Traitement du signal

La séparation passe-bas/passe-bande/passe-haut, l'application effective des
gains, l'écoute des bandes, leur recombinaison et l'export du mix sont laissés à
implémenter par le groupe, comme prévu pour le projet. L'interface signale
explicitement ces éléments en attente ; elle ne prétend pas appliquer les gains
à l'audio tant que le DSP n'est pas branché.

Le contrat Python prévu pour ce traitement est décrit dans
`dsp_backend.py`. L'ancienne interface de bureau Python se trouve toujours dans
`egaliseur_app.py`; la nouvelle interface web est `index.html`, `styles.css` et
`app.js`.

## Tests Python

Les utilitaires audio Python existants se vérifient avec :

```powershell
python -B -m unittest -v
```
