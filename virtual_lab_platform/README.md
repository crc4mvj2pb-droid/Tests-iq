# Virtual Lab Platform

**Laboratoire scientifique virtuel local, multidisciplinaire et extensible.** Prototype de recherche : une entrée de catalogue ne signifie pas qu'une simulation correspondante existe. Les résultats calculés ne sont pas des mesures expérimentales.

## Version actuelle

La version actuelle est définie dans `version.py`. À la racine se trouvent ses notes (`RELEASE_NOTES_v<version>_FR.md`), sa matrice de validation générée (`VALIDATION_MATRIX_v<version>.md`) et le rapport de tests généré (`TEST_RESULTS_v<version>.txt`). Installation, mise à jour et vérification : **`INSTALLATION_FR.md`**.

Les documents de toutes les versions précédentes sont conservés dans `docs/history/`. La feuille de route et le brief d'audit sont dans `docs/`.

## Démarrage rapide

- Python 3.10 ou plus récent; aucun paquet Python tiers requis pour lancer le serveur.
- Mac/Linux : `sh launch_macos_linux.sh`
- Windows : double-cliquer sur `launch_windows.bat`.
- Ouvrir `http://127.0.0.1:8765`.

Le serveur écoute sur la boucle locale. Ne pas l'exposer directement à Internet.

## Nouveauté v2.7 : le circuit graphique devient calculable

Les composants électriques affichent des bornes nommées (`+`, `−`, `A`, `B`, `GND`). Un câble relie deux bornes précises. Les connexions sont converties en nœuds électriques, puis en netlist envoyée au solveur nodal CC. Le résultat comprend les tensions de nœuds, les courants, les chutes de tension, les puissances, la résistance équivalente, les contrôles de Kirchhoff et le bilan de puissance.

Pour le premier circuit, ajouter une source CC, une résistance et une masse; relier `+` à `A`, `B` à `GND`, puis `−` à `GND`; cliquer sur **Résoudre le circuit CC câblé**. Les valeurs sont modifiables dans Propriétés. La paillasse et les câbles sont sauvegardés localement et exportables en JSON.

### Domaine pris en charge par ce solveur graphique

Une source idéale CC, une masse de référence, des fils idéaux et des résistances linéaires. Les condensateurs, inductances, interrupteurs, diodes, transistors et sources alternatives ne sont pas encore intégrés à ce solveur graphique. Des solveurs analytiques RC/RL et RLC séparés sont disponibles, mais ils ne sont pas automatiquement déduits du câblage de la paillasse. Ce n'est pas un remplacement de SPICE.

## Autres fonctions conservées

- Paillasse bilingue FR/EN au minimum, avec options NL/ES, bibliothèque catégorisée et export JSON.
- Placement d'échantillons dans des machines, avec opérations explicitement prises en charge (par exemple, consigne thermique, Beer–Lambert avec paramètres fournis et bilans stœchiométriques limités).
- Modèles numériques de cinétique enzymatique, croissance, réactions du premier ordre, pharmacocinétique pédagogique, dynamique prédateur-proie, neurone simplifié, SIR, diffusion thermique et autres modèles listés dans le registre.
- Analyse d'incertitude Monte Carlo, sensibilité, balayage de paramètres, ajustement de paramètres et comparaison aux données de référence.
- Analyse descriptive de CSV, import SBML partiel, provenance, dossier JSON, historique SQLite et outils de protocole.

## Vérification

Voir `INSTALLATION_FR.md`, section 4 : `python scripts/run_validation.py` génère la matrice de validation à partir des tests réellement exécutés. Les tests logiciels ne remplacent ni une validation scientifique indépendante, ni une vérification physique.

## Architecture principale

- `app.py` : serveur HTTP local (bibliothèque standard), routes de l'API, contrôle `Host`/`Origin`.
- `static/index.html` : interface (paillasse, chimie, instruments, historique, outils de recherche).
- `experiment_service.py` : cycle de vie des expériences (calcul → dossier → enregistrement → vérification → rejeu → export/import).
- `dossier.py` : format de dossier unique (schéma 2), empreintes et vérification à trois niveaux.
- `history.py` : historique SQLite avec migration de schéma et sauvegarde automatique.
- `electrical_circuits.py`, `workbench_circuit.py` : solveur nodal CC (raffinement en précision mixte, incertitudes) et diagnostic de topologie de la paillasse.
- `chemical_kinetics.py`, `reaction_stoichiometry.py` : cinétique RK4 avec estimation d'erreur, stœchiométrie avec contrôle des éléments.
- `virtual_instruments.py`, `linked_measurements.py` : mesures simulées, et mesures reliées aux dossiers.
- `electrical_advanced.py`, `models.py`, `research_tools.py`, `sbml_engine.py`, `lab_designer.py`, `protocol_engine.py` : autres modèles et outils (niveaux de vérification variables, voir la documentation de chaque version).
- `scientific_library/` : catalogue, connaissances, constantes, unités et sources.
- `tests/` : tests unitaires, d'API et de navigateur (`tests/browser/`, Playwright).
- `scripts/` : validation générée, audit d'accessibilité, vérification de syntaxe, construction et vérification des archives.

## Limites globales

Le logiciel ne contient pas « tout ce que l'humanité connaît » et ne prétend pas le faire. La couverture doit grandir par intégration de bases de données scientifiques sourcées, avec provenance, licence, unités, incertitudes et domaine de validité. Les objets conceptuels, les modèles pédagogiques et les résultats calculés doivent rester clairement distingués.


## v2.8 — Chemical reaction-network kinetics

A new local endpoint, `POST /api/chemistry/kinetics`, integrates user-defined concentration-based reaction networks using fixed-step RK4. It supports elementary mass-action rate laws, constant-temperature Arrhenius scaling when activation energy is supplied, optional per-reaction atom-balance checks when formulas are provided, bounded network sizes, and explicit stability/error guards. See `RELEASE_NOTES_v2.8_FR.md` for the request format and limitations.

## v3.0 — interface de cinétique chimique
La v3.0 relie le solveur de réactions de v2.8 à un panneau interactif de l’interface. Voir `README_v3.0_FR.md`, `DEMARRAGE_RAPIDE_v3.0_FR.md` et `RELEASE_NOTES_v3.0_FR.md`.
