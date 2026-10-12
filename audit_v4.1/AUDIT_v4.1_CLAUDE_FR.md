# Audit technique et scientifique indépendant — Virtual Lab Platform v4.1

**Auditeur :** Claude (audit indépendant, sans modification du code)
**Date :** 12 octobre 2026
**Base auditée :** `virtual_lab_platform_v4_1_claude_handoff.zip` (identique à `virtual_lab_platform_v4_1.zip` + 3 documents de passation : vérifié par `diff -rq`)
**Environnement :** Linux, Python 3.13.16, pytest 9.1.1 (installé dans un venv isolé), Node.js 22.22.0, Playwright 1.56.1 + Chromium 1194 (headless)
**Règle suivie :** chaque constat cite un fichier, une fonction, une commande ou un résultat observé. Ce qui n'a pas été exécuté est marqué comme tel. Aucun fichier du projet n'a été modifié ; tous les essais ont tourné sur une copie, avec une base SQLite jetable.

---

## 1. Résumé exécutif

**Ce qui marche réellement.** Le parcours électrique de la paillasse marche de bout en bout dans un vrai navigateur Chromium. Le test a cliqué chaque étape : ajout de 3 composants, modification des valeurs, câblage borne à borne, calcul, affichage, enregistrement SQLite, vérification de l'empreinte, rejeu, sauvegarde, rechargement, restauration et suppression. Le circuit de référence 9 V / 1 kΩ donne 9,0000 mA et 81,000 mW, avec un résidu KCL nul et un bilan de puissance nul. Le solveur CC, le moteur de cinétique et la stœchiométrie donnent des résultats corrects sur des cas indépendants. Pour la cinétique, l'écart aux solutions analytiques est d'environ 1e-11.

**Les rapports v4.0/v4.1 sont exacts sur ce qu'ils affirment** : 170 tests passent, la compilation et la syntaxe JS sont bonnes, et le rejeu par l'API marche. Leurs limites étaient annoncées honnêtement. En revanche, ils ne voient pas plusieurs défauts que seuls des essais réels font apparaître :

- **Bloquant** : `POST /api/lab/run` (le bouton « Run » du concepteur d'expériences) échoue **toujours** avec une erreur 500. Cause : une variable non définie (`app.py:214`).
- **Majeur** : seuls les dossiers électriques sont vérifiables. Les expériences de modèles sont enregistrées avec `model_id = "unknown"` et sans empreinte reconnue. Les protocoles n'ont pas de configuration, donc ne sont pas vérifiables.
- **Majeur** : la chimie (cinétique, stœchiométrie) n'est **jamais enregistrée** dans l'historique.
- **Majeur** : la reproductibilité est partielle. Le contrôle d'intégrité ne couvre pas les résultats, il n'y a pas de version du moteur dans les dossiers, et l'application ne compare pas le résultat rejoué au résultat d'origine.
- **Majeur** : un double-clic crée deux dossiers. Un corps JSON qui n'est pas un objet provoque une erreur 500, et cette erreur n'est pas journalisée.

**Pourquoi la suite de tests ne les voit pas** : environ 57 assertions des tests « interface » (v3.4 → v4.1) vérifient seulement qu'une chaîne de caractères est présente dans `index.html`. Aucune ne clique. Les tests du concepteur appellent `run_lab_experiment()` directement, jamais l'endpoint HTTP.

**Point important pour la suite** : les rapports précédents disaient que le test Chromium était impossible. Dans mon environnement, il est possible et je l'ai fait. Un harnais Playwright est donc faisable pour la v4.2.

---

## 2. Architecture et flux réels

```
static/index.html (1139 lignes, 278 Ko, 3 blocs <script>)
  ├─ bloc 1 (l.273–745)  : portée globale — modèles, historique, recherche, SBML, concepteur
  ├─ bloc 2 (l.745–1122) : IIFE — paillasse, câblage, chimie, cinétique, électricité
  └─ bloc 3 (l.1122–fin) : IIFE — instruments virtuels
        │  fetch JSON
        ▼
app.py — http.server.ThreadingHTTPServer 127.0.0.1:8765 (aucune dépendance tierce)
  ├─ GET  /api/health, /api/version, /api/models, /api/lab/catalog, /api/library, /api/units, ...
  ├─ GET  /api/history, /api/history/{id}, /api/history/{id}/verify
  ├─ POST /api/electrical/workbench-run ──► workbench_circuit.solve_workbench_circuit
  │                                         └► electrical_circuits.solve_dc_circuit (nodal, Gauss-Jordan)
  │                                         └► experiment_lifecycle.configuration_hash ──► history.save_experiment
  ├─ POST /api/history/{id}/replay ──► verify_dossier_integrity ──► même solveur ──► nouveau dossier (replay_of)
  ├─ POST /api/chemistry/kinetics ──► chemical_kinetics (RK4 pas fixe)          [non enregistré]
  ├─ POST /api/chemistry/stoichiometry ──► reaction_stoichiometry                [non enregistré]
  ├─ POST /api/instruments/measure ──► virtual_instruments (valeur « vraie » fournie par l'appelant)
  ├─ POST /api/experiments ──► engine.run_experiment ──► history (schéma différent !)
  ├─ POST /api/protocol/run, /api/lab/run ──► protocol_engine, lab_designer, equipment_models
  └─ POST /api/import-sbml, /api/import-dataset ──► scientific_library/imported_assets/ (écriture disque)
        ▼
history.py — SQLite `virtual_lab_history.sqlite3` à côté du code source ; 1 table, pas de version de schéma
Paillasse : localStorage du navigateur (clé `vl-bench`, 1 seul emplacement) + export JSON (sans import)
```

Point d'entrée réel : `python app.py` (ou `launch_macos_linux.sh` / `launch_windows.bat`). La seule dépendance de test est pytest, et elle n'est déclarée nulle part.

---

## 3. Tableau des problèmes

Gravité : **B** = bloquant, **M** = majeur, **m** = mineur, **c** = cosmétique.
Preuve : **[exécuté]** = observé en lançant le code ; **[code]** = constaté à la lecture seule.

| # | Grav. | Fichier / fonction | Preuve | Conséquence | Correctif recommandé |
|---|---|---|---|---|---|
| 1 | **B** | `app.py:214`, branche `/api/lab/run` | [exécuté] Une requête acceptée par `/api/lab/validate` et `/api/protocol/validate` (`valid: true`) renvoie **500**. La trace interceptée en processus donne `UnboundLocalError: cannot access local variable 'configuration'`. Dans Chromium, le bouton `#labRun` affiche « Run blocked: Internal error » (capture `03_lab_run.png`). | Le concepteur d'expériences ne peut jamais lancer d'expérience ni l'enregistrer. | Utiliser `result.get("configuration", {})`. Ajouter un test HTTP de `/api/lab/run`. |
| 2 | **M** | `engine.py:34-40` contre `history.py:32-35` | [exécuté] Une expérience lancée par `#run` est enregistrée avec `model_id: "unknown"`, `title: "unknown experiment"` et `configuration_hash: null`, alors qu'elle contient `model.id = "enzyme_kinetics"` et `configuration_sha256`. `/verify` → `valid: false`. | Historique illisible pour les modèles. Le bouton de vérification échoue sur des dossiers corrects. | Un seul schéma de dossier (`model_id`, `configuration`, `configuration_hash`), avec une fonction commune de construction du dossier. |
| 3 | **M** | `app.py:191-196`, `/api/protocol/run` | [exécuté] Le dossier n°9 n'a pas de clé `configuration` → `/verify` = « no verifiable configuration hash ». | Les protocoles ne sont pas vérifiables, alors que l'interface propose le bouton. | Enregistrer la configuration du protocole. Masquer ou désactiver Vérifier/Rejouer quand ce n'est pas applicable. |
| 4 | **M** | `experiment_lifecycle.py:84-97` | [exécuté] Résultats modifiés directement en SQLite (`source_current_a = 123`) → `/verify` reste `valid: true` et l'interface afficherait « ✓ ». Configuration + empreinte réécrites ensemble → toujours `valid: true`. La colonne `configuration_hash` (ancienne valeur) n'est jamais comparée à celle du dossier. | « Intégrité » veut dire ici « la configuration n'a pas été corrompue par accident ». Ce n'est ni une protection des résultats ni une protection contre une falsification. C'est documenté, mais le libellé « ✓ » est trompeur. | Empreinte du dossier complet (configuration + résultats + version du moteur), comparée à la colonne. Libellé précis dans l'interface. |
| 5 | **M** | `app.py:127-148` (rejeu) | [exécuté] Aucun champ de version (moteur, code, Python) dans le dossier électrique. Le rejeu recalcule avec le code actuel et ne compare pas les résultats. Seul le test `test_v41_reproducibility.py:67` le fait. | Si le solveur change, un rejeu donne silencieusement un autre résultat, et personne ne le voit. | Enregistrer `engine_version` et `app_version`. Renvoyer et afficher un comparatif d'origine contre rejeu avec une tolérance. |
| 6 | **M** | `app.py:151-154` | [exécuté] Après stœchiométrie et cinétique dans Chromium, l'historique ne contient aucun dossier chimique. | Pas de traçabilité ni de rejeu pour la chimie (prévu en v4.6). | v4.6 : endpoints `*-run` sur le modèle de l'électricité. |
| 7 | **M** | `index.html:1008` `runWorkbenchCircuit` | [exécuté] Un double-clic sur « Résoudre » → **2 dossiers** créés. | Historique pollué, doublons trompeurs. | Désactiver le bouton pendant la requête (et le même principe pour tous les boutons qui enregistrent). |
| 8 | **M** | `app.py:126`, `268-270` | [exécuté] Corps `[1,2]` ou `"x"` → **500** (`AttributeError: 'list' object has no attribute 'get'`). Le message dit « Check the local terminal logs », mais `server.log` ne contient aucune trace. | Erreurs utilisateur présentées comme pannes internes. Diagnostic impossible. | Exiger un objet JSON (400). `traceback.print_exc()` ou `logging.exception` dans le `except Exception`. |
| 9 | **M** | `app.py` (pas de contrôle `Origin`/`Host`) | [exécuté] POST `Content-Type: text/plain` avec `Origin: https://evil.example` → **200** et dossier créé. En-tête `Host: attacker.example` accepté. | Une page web visitée pourrait écrire dans l'historique ou importer des fichiers (CSRF local, DNS rebinding). L'exposition réelle dépend des protections du navigateur. Non testé depuis un site tiers réel. | Refuser `Host` ≠ `127.0.0.1`/`localhost`, refuser les `Origin` étrangers et exiger `application/json`. |
| 10 | **M** | `index.html:884-885` | [code] Sauvegarde = 1 seul emplacement `localStorage`. L'export JSON (`schema_version: 2`) n'a **pas d'import** (0 occurrence de `wbImport`/`importWorkspace`). La sauvegarde interne a `version: 4`, sans migration. La restauration ne filtre pas les fils vers des composants absents (`filter(e=>e&&e.a&&e.b)`). | Perte de travail en changeant de navigateur ou en vidant les données. Fils orphelins possibles après restauration d'un fichier modifié. | v4.5 : import/export validés et versionnés, migration explicite. |
| 11 | m | `index.html:368` (rejeu dans l'historique) | [exécuté] Le message de confirmation est vide à 150 ms et à 950 ms : `refreshHistory()` reconstruit la liste et l'efface. | L'utilisateur ne voit pas que le rejeu a réussi. | Afficher la confirmation après le rafraîchissement, ou dans une zone persistante. |
| 12 | m | `index.html:1008` (gestion d'erreur) | [exécuté] Erreur réseau → « Failed to fetch ». Réponse non JSON → « Unexpected token '<' … is not valid JSON ». Champ résistance vide → message « resistor:7e73069a-…: resistance must be … > 0 Ω » (UUID interne, et un champ vide devient 0). | Messages bruts et peu compréhensibles. | Messages traduits, nom affiché plutôt qu'UUID, refus explicite du champ vide. |
| 13 | m | `workbench_circuit.py:278,284` | [exécuté] `qty: true` → accepté comme 1 Ω (I = 9 A). | Valeur non numérique acceptée en silence. | Refuser les booléens, comme le fait déjà `chemical_kinetics._finite_number`. |
| 14 | m | `electrical_circuits.py:334` contre `:369` | [exécuté] Le validateur accepte R ≤ 1e15 Ω, mais 2 × 1e15 Ω en série → « Circuit matrix is singular » (seuil de pivot absolu 1e-14). 2 × 2e14 Ω passe. | Refus erroné en très haute impédance, avec un message trompeur. | Seuil relatif, ou mise à l'échelle des conductances. Plage validée cohérente. |
| 15 | m | `electrical_circuits.py:335` / `workbench_circuit.py` | [exécuté] Une boucle de résistances isolée de la source → message générique « singular ». Une LED posée mais non câblée est ignorée sans mention dans le résultat. | Diagnostic de topologie incomplet (prévu en v4.4). | Détecter les composantes connexes avant le calcul et nommer les composants flottants ou ignorés. |
| 16 | m | `chemical_kinetics.py:69-87,113,136-149` | [exécuté] IDs de réaction en double acceptés (`final_rates` n'a plus qu'une clé). Réaction H₂ + O₂ → H₂O non équilibrée simulée quand même (simple drapeau `False`). RK4 à pas fixe sans estimation d'erreur : à k·dt = 1,5, A(1) = 2,51e-7 au lieu de 3,06e-7 (−18 %), sans avertissement. | Résultats imprécis présentés comme valides. Bilan atomique non bloquant. | Unicité des IDs. Blocage (ou statut explicite) si déséquilibre. Contrôle par doublement du pas ou pas adaptatif (v5.2). |
| 17 | m | `reaction_stoichiometry.parse_formula` | [exécuté] Le symbole inconnu `Xy` est accepté. Sans formules, le calcul aboutit (je n'ai pas vérifié si la sortie signale l'absence de contrôle atomique). | Une formule invalide passe le contrôle « vérifié ». | Liste des éléments réels (v5.1/v6.0). |
| 18 | m | `app.py:124` | [exécuté] POST `/replay` sans corps → 413 « Request body missing or too large ». | Code HTTP faux pour un endpoint qui n'a pas besoin de corps. | Corps facultatif pour le rejeu. |
| 19 | m | `virtual_instruments.py:35` | [code] La lecture simulée part d'une `true_value` fournie par l'appelant. Elle n'est reliée à aucun moteur. | Conforme à la doc, mais pas de provenance (prévu en v4.7). | v4.7. |
| 20 | m | Tests `test_v34…v41_*.py` | [code] Environ 57 assertions du type `assert "..." in html`. `app_test.py` (230 l.) est une ancienne copie de `app.py` que rien n'utilise. | Une fonctionnalité peut être déclarée « testée » sans qu'aucun clic ne la vérifie. Explique l'absence de détection du n°1. | Tests navigateur réels (v4.2). Supprimer ou archiver `app_test.py` en le signalant. |
| 21 | m | `index.html` bloc 2 | [exécuté + code] 6 fonctions déclarées deux fois dans la même IIFE (`addItem`, `renderBench`, `renderInspector`, `renderCatalog`, `visualFor`, `download`). La seconde l'emporte : l'ancienne est du code mort. Exemple : l'ancienne version de `wbPropQty` imposait ≥ 0, la version active non. Pas de conflit global, vérifié dans Chromium (`download` global = version du bloc 1). | Maintenance risquée : on peut corriger la mauvaise copie. | Supprimer les versions mortes en v4.3, sous tests navigateur. |
| 22 | c | `index.html:2`, `README.md` | [exécuté] `<title>` = « Virtual Lab Platform v3.6 ». `README.md` annonce « v3.4 ». Plus de 60 fichiers README/RELEASE/TEST versionnés à la racine. `unittest discover` ne trouve que 110 tests sur 170. pyflakes : 8 imports inutilisés, variables `canonical_config` inutilisées (`app.py:164,213`), clé `'k'` répétée (`scientific_copilot.py:35,39`). | Confusion sur la version réelle. | Version unique (un seul fichier), docs anciennes dans `docs/history/`. |

---

## 4. État des fonctions

### Opérationnel de bout en bout (vérifié)
- **Paillasse électrique CC**, avec 14 étapes cliquées dans Chromium : ajouter → modifier → câbler → résoudre → afficher → SQLite → vérifier → rejouer → exporter → sauvegarder → recharger → restaurer → résoudre à nouveau → supprimer (0 fil orphelin).
- **Solveur CC** : série 1 k + 2 k → 3 mA, nœud à 6 V. Parallèle 1 k ∥ 1 k → 18 mA, Req = 500 Ω. Diviseur 2 × 1e14 Ω → 4,5 V. 1 mΩ + 1 GΩ cohérent. Erreurs bien détectées : source court-circuitée, résistance shuntée, borne non câblée, deux sources, condensateur connecté, fil vers un composant absent, R = 0, R = « 1k », V = Infinity.
- **Empreinte et rejeu électriques** : empreinte stable. Une configuration modifiée est détectée et le rejeu est alors refusé (409). Le rejeu crée un nouveau dossier `replay_of` avec un courant identique.
- **Stœchiométrie** (API et interface) : 2H₂ + O₂ → 2H₂O (O₂ limitant, avancement 1 mol). Ca(OH)₂ + 2HCl (HCl limitant, 0,5 mol). Rejet des équations non équilibrées.
- **Cinétique** (API et interface) : écart relatif aux solutions analytiques ≤ 4e-11 pour le 1er ordre, le 2nd ordre (2A → P), A → B → C et Arrhenius (Ea = 50 kJ/mol). Équilibre A ⇌ B : rapport 2,000. L'interface affiche [A] = 0,135335 = e⁻².
- Tous les endpoints GET listés répondent 200, et 400/404 pour les ID invalides.

### Partiel
- Historique : électricité seulement. Modèles enregistrés en « unknown ». Protocoles non vérifiables. Chimie absente.
- Reproductibilité : configuration seulement. Ni résultats, ni version du moteur, ni comparatif dans l'application.
- Sauvegarde de la paillasse : 1 emplacement local, export sans import, pas de migration.
- Diagnostics de topologie : bons sur les cas courants, génériques pour les sous-réseaux flottants.
- Gestion d'erreurs de l'interface : présente mais brute, pas d'anti-double-clic.

### Simulé ou illustratif (et présenté comme tel)
- Instruments virtuels (lecture bruitée autour d'une valeur fournie), catalogue d'équipements, valeurs de performance, modèles « L0 / workflow_template ».

### Cassé
- `/api/lab/run` (n°1).

### Non vérifié par moi (seulement couvert par les tests du projet, qui passent)
- RC/RL, RLC AC et balayage fréquentiel (`electrical_advanced.py`), simulateur SBML et ses balayages, les 13 modèles de `models.py`, outils de recherche (ajustement, Monte Carlo, sensibilité), analyse CSV, copilote scientifique, imports SBML/CSV de bout en bout, accessibilité clavier, langues NL/ES, Safari/macOS.

---

## 5. Tests exécutés (résultats exacts)

| Commande / essai | Résultat |
|---|---|
| `python -m pytest -q` (Python 3.13.16, pytest 9.1.1) | **170 passed in 2.26s** |
| `python -m unittest discover -s tests -q` | **Ran 110 tests — OK** (les 60 tests de style pytest ne sont pas découverts) |
| `python -m py_compile *.py tests/*.py scripts/*.py` | OK |
| Extraction des 3 blocs `<script>` + `node --check` | 3/3 OK |
| `python -m pyflakes *.py` | Aucun nom indéfini détecté ; 8 imports inutilisés, 3 variables inutilisées, 1 clé dupliquée |
| 15 endpoints GET avec `curl` | 200 (et 400/404 attendus) |
| Circuit de référence 9 V / 1 kΩ : run → verify → replay (`curl`) | I = 0,009 A, P = 0,081 W, KCL = 0, empreinte valide, rejeu #2 `replay_of: 1`, courant identique |
| 16 cas limites électriques (`preuves/scripts/edge.py`) | voir n°13–15 et section 4 |
| Falsification SQLite (`tamper.py`) | voir n°4 |
| `/api/lab/run` HTTP + trace en processus (`labrun.py`, `inproc.py`) | 500, `UnboundLocalError` |
| Cinétique contre solutions analytiques (`kin.py`, `kin2.py`) | voir section 4 et n°16 |
| Stœchiométrie (`sto.py`) | voir section 4 et n°17 |
| Requêtes cross-origin (`curl`) | voir n°9 |
| **Chromium headless — `audit.js`** | 11 PASS, 1 WARN (double-clic), 0 erreur JS ; 2 erreurs console provoquées volontairement (réseau coupé, 502) |
| **Chromium headless — `audit2.js`** | métriques affichées correctes ; messages d'erreur (n°12) ; message de rejeu vide (n°11) ; chimie OK mais non enregistrée ; `#labRun` en erreur 500 |

Les scripts, le journal `browser_audit_log.json` et 3 captures sont dans `audit_v4.1/preuves/`.

**Non exécuté ou impossible ici** : Safari ou Chrome sur macOS ; lanceurs `.sh`/`.bat` (j'ai lancé directement `python app.py`) ; attaque CSRF depuis un vrai site tiers ; glisser-déposer à la souris (seuls les boutons « + Ajouter » ont été testés) ; navigation au clavier ; comparaison avec ngspice ; vérification indépendante des modules listés en « non vérifié ».

---

## 6. Les cinq améliorations prioritaires

1. **Réparer `/api/lab/run` et ajouter des tests HTTP pour chaque endpoint qui enregistre** (n°1, n°20). C'est la seule panne bloquante. La correction tient en une ligne, mais le vrai problème est l'absence de test de l'endpoint.
2. **Mettre en place des tests navigateur reproductibles (Playwright)** pour le parcours électrique, puis la chimie et la sauvegarde (n°7, 11, 12, 20). C'est faisable : je l'ai fait pendant cet audit. Ces tests remplacent les assertions « chaîne présente dans le HTML ».
3. **Un seul schéma de dossier d'expérience** pour tous les endpoints qui enregistrent : `model_id`, `configuration`, `configuration_hash`, `engine_version`, `app_version`, `data_status` (n°2, 3, 5). C'est le prérequis de toute la reproductibilité (v4.5, v4.6, v6.4).
4. **Une intégrité et un rejeu honnêtes** : empreinte du dossier complet comparée à la colonne SQLite, comparatif d'origine contre rejeu affiché, libellé exact dans l'interface (n°4, 5).
5. **Durcir le serveur local** : objet JSON exigé (400), journalisation des 500, contrôle `Host`/`Origin`/`Content-Type`, anti-double-soumission (n°7, 8, 9).

---

## 7. Proposition pour la v4.2 — portée limitée

**Objectif unique :** *le parcours électrique de référence et ses erreurs courantes sont vérifiés par des tests navigateur automatisés et reproductibles, et les défauts bloquants ou majeurs rencontrés sur ce parcours sont corrigés.*

**Dans la portée :** harnais Playwright (dépendance de développement seulement : l'application reste sans dépendance) ; correction n°1 (lab/run, car c'est le seul bloquant) ; corrections n°7, 8, 11, 18 (elles touchent directement le parcours) ; matrice de validation générée.
**Hors portée (versions suivantes) :** schéma de dossier unifié (n°2–5), chimie dans l'historique, import et migration, refonte de `index.html`, sécurité Origin/Host (n°9, à planifier en v4.3 ou v4.5), modèles électriques avancés.

### Critères d'acceptation (tous vérifiables par une commande)

| # | Critère | Vérification |
|---|---|---|
| CA1 | Aucune régression : ≥ 170 tests pytest passent, aucun test supprimé ni désactivé | `python -m pytest -q` |
| CA2 | Une commande unique lance un serveur sur un port libre avec une base SQLite temporaire, exécute les tests navigateur et renvoie 0. En cas d'échec, une capture et la trace sont écrites dans `test-artifacts/` | ex. `python scripts/run_browser_tests.py` |
| CA3 | Parcours nominal cliqué : 3 composants ajoutés ; valeurs 9 V et 1000 Ω saisies ; 3 fils ; affichage de 0,0090000 A et 0,081000 W ; exactement 1 dossier dans `/api/history` ; « ✓ » à la vérification ; rejeu → dossier n°2 avec `replay_of = 1` et \|ΔI\| < 1e-12 ; confirmation visible ≥ 2 s ; sauvegarde → rechargement → 3 composants et 3 fils restaurés ; suppression → 0 fil orphelin | tests navigateur |
| CA4 | Un double-clic sur « Résoudre » crée exactement 1 dossier | test navigateur |
| CA5 | 6 cas d'erreur depuis l'interface (source court-circuitée, résistance shuntée, borne libre, deux sources, condensateur câblé, réseau coupé) : message compréhensible, sans UUID, et **aucun dossier créé** | tests navigateur |
| CA6 | `/api/lab/run` avec la requête de `tests/test_lab_designer.py` + `protocol_steps` → 200 et dossier enregistré | nouveau test HTTP |
| CA7 | Corps `[1,2]`, `"x"` ou vide sur un endpoint qui enregistre → 400 avec un message explicite ; `/replay` sans corps accepté ; toute erreur 500 écrit une trace dans le journal du serveur | tests HTTP (capture de stderr) |
| CA8 | Aucune erreur JavaScript (`pageerror`) ni erreur console sur le parcours nominal | test navigateur |
| CA9 | `VALIDATION_MATRIX_v4.2.md` **générée par l'exécution** (fonctionnalité / étapes / attendu / observé / statut passé-échoué-ignoré-impossible / preuve), sans chiffre écrit à la main | fichier produit par la commande CA2 |
| CA10 | La documentation dit clairement ce qui n'est pas testé (Safari/macOS, glisser-déposer, clavier) | relecture |

---

## 8. Pour la comparaison avec l'audit de ChatGPT

- J'ai **confirmé** les affirmations chiffrées du rapport v4.1 : 170 tests, compilation, 3 blocs JS, rejeu 9 V / 1 kΩ.
- Je **corrige** une limite annoncée : un test Chromium réel est possible (Playwright 1.56 + Chromium headless).
- Mes constats que les rapports précédents ne mentionnent pas : n°1 (lab/run cassé), n°2–3 (schéma de dossier incohérent), n°7 (double soumission), n°8 (500 non journalisées), n°9 (requêtes cross-origin acceptées), n°11 (confirmation de rejeu invisible), n°16 (imprécision RK4 sans avertissement).
- Une fausse piste que j'ai écartée en la testant : les fonctions JavaScript en double **ne** créent **pas** de conflit global (bloc 2 isolé dans une IIFE). C'est du code mort, pas un bug actif.
