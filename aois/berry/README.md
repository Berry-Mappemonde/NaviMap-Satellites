# Campagne Berry-Mappemonde

Fenêtres côtières pour commencer l’atlas — **pas** l’itinéraire officiel, **pas** une carte marine.

## Ordre de travail

1. **expedition** — baies déjà décrites ici (Calvi + quelques lagons ultramarins clairs).
2. **route** — autres segments de la circumnavigation, à ajouter une bbox à la fois.
3. **world** — le reste des côtes *optiquement possibles*, jamais le globe d’un coup.

Sentinel-2 ne voit pas un écueil d’un mètre, ni un « continent de plastique ».
Il peut montrer un trait de côte, de grands plats clairs, et une profondeur
approximative si l’eau est claire et si on cale Stumpf.

## Commandes

```bash
navimap-sat campaign aois/berry
navimap-sat campaign aois/berry --phase expedition --search
navimap-sat process aois/calvi.yaml --out work/calvi
```

`process` télécharge un L1C (compte Data Space), lance ACOLITE, écrit des GeoJSON.
Sans ACOLITE ni compte, `campaign` et `search` suffisent pour préparer la liste.
