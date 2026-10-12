# Guide d'utilisation — Virtual Lab Platform

L'interface est une seule page. Chaque section ci-dessous correspond à un panneau de la page.

## 1. Paillasse électrique
Ajoutez une source CC, des résistances et une masse depuis la bibliothèque, puis reliez les bornes. « Résoudre » calcule tensions, courants, puissances et bilans, et **enregistre un dossier** dans l'historique. Un condensateur ou une bobine permet un transitoire du premier ordre. Les erreurs de câblage (réseau flottant, court-circuit) sont nommées.

## 2. Chimie
- **Stœchiométrie** : réactif limitant et bilan atomique.
- **Cinétique** : réseau de réactions, avec choix de l'intégrateur (RK4, adaptatif, implicite pour les systèmes raides) et estimation d'erreur.
- **Équilibres acide–base** : par l'API (`aqueous_acid_base`) ou par l'assistant (« pH d'une solution d'acide acétique à 0,1 mol/L »).

## 3. Instruments reliés
Une lecture simulée (multimètre, spectrophotomètre…) d'une grandeur d'un dossier enregistré, avec son budget d'incertitude. **C'est une simulation, pas une mesure.**

## 4. Historique
Pour chaque expérience : **Vérifier** (intégrité), **Rejouer** (recalcul et comparaison), **Exporter**, **Rapport** (méthode, paramètres, résultats, incertitudes, références ; conclusions à rédiger par vous) et **Paquet reproductible** (ZIP que n'importe qui peut relancer avec `python reproduce.py`).

## 5. Analyses paramétriques
Balayage, sensibilité locale et Monte Carlo sur n'importe quel modèle à contrat, en tâche de fond annulable, avec export CSV.

## 6. Expériences multi-modèles
Des chaînes comme circuit → échauffement → Arrhenius → cinétique, avec unités contrôlées à chaque liaison. La maturité d'une chaîne est celle de son maillon le plus faible. Les boutons « Propager les incertitudes » et « Effet des hypothèses » complètent l'analyse.

## 7. Catalogue de données
Recherche et filtre par nature (référence, expérimentale publiée, importée, calculée, simulée), export CSV et bibliographie. **Importer un fichier** : l'aperçu et le contrôle qualité passent d'abord ; votre fichier est conservé à l'identique.

## 8. Ajustement de modèles
Choisissez un jeu, des colonnes, un modèle et éventuellement une validation séparée. Vous obtenez estimations ± erreurs types, IC 95 %, résidus et diagnostics. Hors de la plage ajustée, toute prédiction est une extrapolation.

## 9. Domaines scientifiques
Pour chaque domaine : périmètre, exclusions, cas de référence et niveau de validation.

## 10. Assistant scientifique (à règles)
- **Demander** : calcul tracé (chaque nombre renvoie à son appel d'outil).
- **Formuler** : variables et hypothèses H1, H2, H0.
- **Concevoir le protocole**, **Exécuter le plan** (annulable), **Analyse critique**.
- **Valeur cible** puis « Trouver le paramètre » et « Retenir ce plan ».

L'assistant répond « inconnu » ou « hors périmètre » plutôt que d'inventer. Il ne donne aucun conseil médical ou financier.

## 11. Sauvegardes et maintenance, projets
Créer, vérifier ou restaurer une sauvegarde ; **Diagnostic** de l'installation. Les projets regroupent des expériences et s'exportent en un ZIP vérifiable, qu'un collègue peut importer.

## Bonnes pratiques
- Les valeurs par défaut sont **illustratives** : remplacez-les par des valeurs sourcées pour une étude réelle.
- Lisez le niveau de maturité et les limites affichés avec chaque résultat.
- Gardez une sauvegarde hors de l'ordinateur (voir le guide d'administration).
