# Notes de version — Virtual Lab Platform v4.7

**Objectif de la version :** relier les lectures simulées des instruments aux résultats des moteurs, en conservant les incertitudes et la provenance.

## Avant / après
- **v4.1–v4.6 :** la « valeur vraie » d'une mesure simulée était saisie à la main. Rien ne la reliait à un calcul.
- **v4.7 :** l'instrument lit une grandeur d'un **dossier enregistré qui a passé la vérification complète** (`level = full`). La lecture est elle-même enregistrée comme dossier `instrument_reading`, avec le statut `simulated_measurement` et `experimental_data: false`.

## Fonctions
- `GET /api/history/{id}/quantities` : grandeurs mesurables d'un dossier, avec leur unité et l'incertitude numérique du modèle :
  - circuit : tensions de nœuds, tensions et courants de branche, courant de source ;
  - cinétique : concentrations finales ;
  - stœchiométrie : quantités produites et restantes.

  La liste des instruments compatibles est donnée par unité.
- `POST /api/instruments/measure-linked` : lecture simulée et enregistrée.
- **Instruments électriques illustratifs** : multimètre tension CC (±(0,5 % + 0,002 V)) et courant CC (±(1 % + 0,02 mA)). La limite de précision est convertie en incertitude-type par division par √3 (loi rectangulaire). Ce ne sont pas des spécifications certifiées.
- **Spectrophotomètre relié à la cinétique** par la loi de Beer–Lambert (A = ε·l·c, avec ε et l fournis). Un avertissement apparaît au-delà d'environ 2 AU, où la linéarité est douteuse.
- **Conversions d'unités explicites** (A → mA, V → mV…). Une unité incompatible est refusée.
- **Budget d'incertitude** : instrument, étalonnage, résolution **et incertitude numérique du modèle** (publiée en v4.4 pour les circuits, en v4.6 pour la cinétique).
- **Provenance** : identifiant et empreinte du dossier source, moteur et version, grandeur, transformation, graine.
- **Rejeu** d'une lecture (même graine → même lecture). Il est refusé si le dossier source a été modifié depuis la mesure.
- Interface : panneau « Mesurer un résultat enregistré » dans la section des instruments.

## Validation
- 7 tests API : valeurs, conversions, budget, provenance, refus, Beer–Lambert et rejeu.
- **Vérification statistique** : sur 2 000 lectures simulées, la proportion où l'intervalle élargi (k = 2) contient la valeur du modèle se situe entre 94 et 97 %. La valeur attendue est 95,45 % pour un bruit gaussien.
- 1 test navigateur couvre le parcours complet : circuit → dossier → multimètre → lecture → rejeu.

## Limites
- Il s'agit toujours de **mesures simulées**, pas de données expérimentales.
- Les spécifications des instruments sont illustratives.
- Les incertitudes sur ε et l ne sont pas propagées.
- L'erreur de forme du modèle (l'écart entre le modèle idéal et la réalité) n'est pas incluse : seule l'incertitude numérique l'est.
- La dérive, l'hystérésis, le temps de réponse et l'impédance d'entrée des appareils ne sont pas modélisés.
