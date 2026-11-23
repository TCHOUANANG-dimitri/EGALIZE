"""Filtres de l'égaliseur — À IMPLÉMENTER après l'étude des filtres.

C'est ici que le groupe écrira le découpage du signal en trois bandes, une fois
les notions comprises. Ordre d'étude prévu :

    1. le filtre passe-bas   -> bande des graves
    2. le filtre passe-haut  -> bande des aigus
    3. le filtre passe-bande -> bande des médiums

La classe à écrire doit respecter le contrat `DSPBackend` (voir dsp_backend.py) :
`split_bands`, `apply_gains` et `recombine_bands`. Une fois prête, remplacez
`BACKEND = None` par `BACKEND = VotreClasse()` : l'étape « Résultat » de
l'application s'activera automatiquement.
"""

from __future__ import annotations

from .dsp_backend import DSPBackend

# Tant que BACKEND vaut None, l'application analyse le signal sans le modifier.
BACKEND: DSPBackend | None = None
