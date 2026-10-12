# Notes de version — v3.9

## Objectif

Rendre les interactions de la paillasse plus accessibles au clavier et mieux annoncées aux technologies d’assistance.

## Modifications

- Les éléments de la paillasse peuvent être sélectionnés avec Entrée ou Espace lorsqu’ils ont le focus clavier.
- Le focus est restauré sur l’élément après son actualisation, pour éviter de perdre sa position pendant la sélection.
- Les catégories de bibliothèque exposent leur état actif via `aria-pressed`.
- Les mises à jour de la bibliothèque et du panneau de propriétés utilisent des régions `aria-live`.
- Ajout d’un nom accessible au champ de recherche et d’un indicateur de focus visible.
- Tests de non-régression dédiés aux attributs d’accessibilité et aux identifiants HTML.

## Limites

Les tests automatisés contrôlent le code et les attributs, mais ne remplacent pas un audit WCAG complet avec lecteur d’écran ni un test manuel dans plusieurs navigateurs. Les interactions souris/tactiles et les calculs scientifiques n’ont pas été modifiés intentionnellement par cette version.
