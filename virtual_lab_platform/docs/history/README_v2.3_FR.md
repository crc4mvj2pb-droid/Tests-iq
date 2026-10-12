# Virtual Lab Platform v2.3 — zone de travail configurable

## Changements
- Renommage de « Paillasse » en « Zone de travail » dans l'interface française et « Workspace » en anglais.
- Les objets de la zone de travail affichent des représentations SVG schématiques adaptées à leur nature : molécule H₂O, ensemble de molécules d'eau, schémas ADN/ARN, résistance, condensateur, inductance et source électrique.
- Le panneau Propriétés expose une valeur numérique et son unité pour les objets dotés d'un paramètre (ex. résistance en Ω, source en V, condensateur en F, bobine en H). La valeur est sauvegardée et affichée sur l'objet.
- Extension du catalogue avec voltmètre, ampèremètre, bécher, tube à essai, éthanol, chlorure de sodium, dioxygène, dioxyde de carbone, ARN, neurone et générateur de signaux conceptuel.
- Les fiches indiquent clairement quand un objet n'est qu'une représentation ou n'est pas relié à un solveur.

## Limites scientifiques
Le catalogue n'est pas exhaustif et ne peut pas représenter « tout ce qui existe ». Les dessins sont des schémas non à l'échelle, pas des rendus atomistiques. Les paramètres ne modifient un résultat que lorsqu'un modèle numérique compatible les utilise. Les circuits à diode/transistor ne sont pas prétendus simulés par le solveur CC résistif. Les modèles biomédicaux restent limités et ne servent pas au diagnostic ni à décider d'expériences médicales.

## Validation logicielle
- 97 tests Python réussis.
- Compilation Python réussie.
- Vérification syntaxique des deux blocs JavaScript réussie avec `node --check`.
