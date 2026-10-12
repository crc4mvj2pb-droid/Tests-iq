# Matrice de validation — Virtual Lab Platform v4.4

Générée automatiquement par `python scripts/run_validation.py` le 2026-10-12T16:05:24+00:00.
Environnement : Python 3.13.16 · Linux-6.18.44-fc-v114-x86_64-with-glibc2.39 · Playwright 1.56.0.

**Résultat global : 533 passés, 0 échoués, 0 ignorés (total 533).** Code de sortie pytest : 0.

| Fonctionnalité | Étapes | Attendu | Observé | Statut | Preuve (test) |
|---|---|---|---|---|---|
| Paillasse : ajout, édition, câblage | Ajouter source, résistance, masse ; saisir 9 V et 1000 Ω ; relier P–A, B–GND, N–GND | 3 composants, valeurs saisies, 3 fils | 3 composants, 3 fils | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Calcul depuis l'interface | Cliquer « Résoudre le circuit CC câblé » | I = 0.0090000 A ; P = 0.081000 W | I = 0.009 A ; P = 0.081 W | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Enregistrement SQLite | Lire /api/history après le calcul | 1 dossier electrical_workbench_dc | 1 dossier(s) | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Vérification d'empreinte | Cliquer « Verify integrity » | Message ✓ | ✓ Configuration hash matches | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Rejeu | Cliquer « Replay circuit » puis attendre 2 s | Nouveau dossier replay_of = original ; \|ΔI\| < 1e-12 ; confirmation visible ≥ 2 s | ✓ Replayed as dossier #2 ; replay_of = 1 ; ΔI = 0.0 | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Sauvegarde et rechargement | Enregistrer, recharger la page, résoudre à nouveau | 3 composants, 3 fils, même courant | 3 composants, 3 fils, I = 0.0090000 A | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Suppression | Supprimer la résistance câblée | 0 fil orphelin | 0 fil orphelin ; 1 fil restant | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Console navigateur | Parcours nominal complet | 0 erreur | 0 erreur(s) | passé | `tests.browser.test_v42_workbench_e2e::test_reference_circuit_full_path` |
| Double soumission | Double-cliquer sur « Résoudre » | 1 dossier | 1 dossier(s) | passé | `tests.browser.test_v42_workbench_e2e::test_double_click_creates_one_dossier` |
| Erreur de topologie : source_short | Construire le circuit invalide puis résoudre | Message compréhensible, sans UUID, aucun dossier | Les bornes + et − de « Source de tension CC » sont reliées directement : la source est en court-circuit. | passé | `tests.browser.test_v42_workbench_e2e::test_topology_errors_are_explained_and_not_saved[source_short]` |
| Erreur de topologie : bypassed | Construire le circuit invalide puis résoudre | Message compréhensible, sans UUID, aucun dossier | Les deux bornes de « Résistance » sont sur le même nœud : la résistance est court-circuitée (shunt) par un fil idéal. | passé | `tests.browser.test_v42_workbench_e2e::test_topology_errors_are_explained_and_not_saved[bypassed]` |
| Erreur de topologie : open_terminal | Construire le circuit invalide puis résoudre | Message compréhensible, sans UUID, aucun dossier | La borne B de « Résistance » n’est pas câblée. Reliez chaque borne avant de résoudre. | passé | `tests.browser.test_v42_workbench_e2e::test_topology_errors_are_explained_and_not_saved[open_terminal]` |
| Erreur de topologie : two_sources | Construire le circuit invalide puis résoudre | Message compréhensible, sans UUID, aucun dossier | Le solveur CC de la paillasse exige une seule source (source CC ou pile) ; 2 trouvée(s). | passé | `tests.browser.test_v42_workbench_e2e::test_topology_errors_are_explained_and_not_saved[two_sources]` |
| Erreur de topologie : capacitor | Construire le circuit invalide puis résoudre | Message compréhensible, sans UUID, aucun dossier | Composant(s) câblé(s) pas encore pris en charge par le solveur CC : Condensateur. Utilisez seulement une source CC, des résistances, des fils et une masse. | passé | `tests.browser.test_v42_workbench_e2e::test_topology_errors_are_explained_and_not_saved[capacitor]` |
| Erreur réseau | Couper la requête de calcul | Message indiquant que le serveur local est injoignable | Le serveur local est injoignable. Vérifiez que « python app.py » est lancé, puis réessayez. | passé | `tests.browser.test_v42_workbench_e2e::test_network_failure_is_reported_and_not_saved` |
| Suppression d'un contenant | Supprimer un bécher contenant une résistance câblée | Contenu et fils supprimés, 0 orphelin | restant : ['r_out'] ; 0 fil | passé | `tests.browser.test_v43_workbench_integrity::test_deleting_a_container_removes_contents_and_their_wires` |
| Restauration d'une sauvegarde altérée | Charger une sauvegarde avec ID dupliqué, élément invalide, fils orphelins/invalides/en double | Nettoyage et compte rendu visibles | Sauvegarde restaurée  2 élément(s) et 1 fil(s) restauré(s). 1 élément(s) invalide(s) ignoré(s) · 1 identifiant(s) dupliqué(s) ignoré(s) · 2 fil(s) orphelin(s) ou invalide(s) retiré(s) · 1 fil(s) en double retiré(s). | passé | `tests.browser.test_v43_workbench_integrity::test_restore_drops_and_reports_invalid_references` |
| Compatibilité des sauvegardes v4.0–v4.2 | Charger une sauvegarde au format {version:4, bench} | Restaurée et calculable | I = 0.0090000 A | passé | `tests.browser.test_v43_workbench_integrity::test_v42_browser_save_format_is_still_restored` |
| Valeur vide | Effacer la valeur de la résistance puis résoudre | Champ signalé, message clair, aucun dossier, valeur non convertie en 0 | indice : Valeur numérique requise : ce composant ne sera pas calculé tant que le champ est vide ou invalide. \| message : Saisissez pour « Résistance » une résistance strictement positive (au plus 1e15 Ω). | passé | `tests.browser.test_v43_workbench_integrity::test_empty_value_is_flagged_and_refused_without_saving` |
| Marquage des composants non calculés | Ajouter un condensateur et une résistance | Seul le condensateur est marqué | condensateur marqué, résistance non marquée | passé | `tests.browser.test_v43_workbench_integrity::test_unsupported_components_are_visibly_marked` |
| Duplication | Dupliquer une résistance câblée | Nouvelle instance, même valeur, aucun fil copié | 2 résistances, 3 fils | passé | `tests.browser.test_v43_workbench_integrity::test_duplicate_copies_values_without_wires` |
| Vider la paillasse | Vider puis ajouter un composant | Aucun fil résiduel | 0 fil | passé | `tests.browser.test_v43_workbench_integrity::test_clear_removes_every_wire` |
| Représentation canonique | Exporter, sauvegarder, recharger, exporter | Composants et fils identiques | identiques | passé | `tests.browser.test_v43_workbench_integrity::test_saved_state_round_trips_identically` |
| Sous-réseau flottant | Ajouter deux résistances reliées entre elles seulement | Composants nommés, aucun dossier | Une partie du circuit n’est reliée ni à la source ni à la masse : Résistance, Résistance. Reliez-la ou retirez-la. | passé | `tests.browser.test_v44_circuit_diagnostics::test_floating_subnetwork_is_named_and_not_saved` |
| Composant ignoré signalé | Ajouter une DEL non câblée au circuit de référence puis résoudre | Résultat inchangé + avertissement visible | ⚠ Composant(s) non câblé(s), non pris en compte dans le calcul CC : DEL. | passé | `tests.browser.test_v44_circuit_diagnostics::test_ignored_component_and_conventions_are_displayed` |

## Non couvert par cette commande

- Safari / macOS et Windows : non exécutés par cette commande (Chromium headless uniquement).
- Glisser-déposer à la souris : non couvert ; les composants sont ajoutés par les boutons « + Ajouter ».
- Lanceurs launch_macos_linux.sh / launch_windows.bat : non exécutés par cette commande.
- Les résultats sont des calculs simulés, pas des mesures expérimentales.
