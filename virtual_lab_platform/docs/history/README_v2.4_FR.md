# Virtual Lab Platform v2.4 — bibliothèque, zone de travail et réactions

## Changements
- Les éléments électriques (source CC, résistance, condensateur, bobine, diode, transistor, voltmètre, ampèremètre et générateur de signaux) sont classés dans « Électricité & électronique ».
- La zone de travail affiche des représentations compactes, sans fiche rectangulaire volumineuse ni description/valeur complète sur chaque objet. Les détails et paramètres restent dans le panneau Propriétés après sélection.
- Ajout d'une catégorie Réactions avec huit bilans stœchiométriques documentés : neutralisation HCl/NaOH, bicarbonate/acide acétique, synthèse de l'eau, décomposition de H₂O₂, combustion complète du méthane, synthèse stœchiométrique de NH₃, bilans globaux simplifiés de photosynthèse et respiration.
- Le calcul détermine le réactif limitant à partir des quantités en mol, diminue les quantités de réactifs et ajoute les quantités théoriques de produits à la zone de travail.
- Ajout d'espèces chimiques au catalogue pour les réactions et d'autres fiches moléculaires/inorganiques.

## Limites importantes
La bibliothèque n'est pas exhaustive : « toutes les molécules et toutes les réactions connues » dépasse largement un catalogue logiciel statique et nécessite des bases de données scientifiques versionnées, des sources/licences, et des contrôles de qualité. Les réactions ajoutées ici sont un ensemble initial, sélectionné et explicitement limité.

Les calculs réactionnels sont des bilans stœchiométriques idéaux. Ils ne prédisent pas les vitesses, les équilibres, les rendements, les produits secondaires, la solubilité, les effets de température/pression, les mécanismes ou les risques. Les bilans de photosynthèse et respiration sont globaux et simplifiés. Les résultats ne constituent pas des protocoles expérimentaux ni des preuves expérimentales.

## Lancement sur macOS
Depuis le dossier extrait : `sh launch_macos_linux.sh`, puis ouvrir `http://127.0.0.1:8765`.
