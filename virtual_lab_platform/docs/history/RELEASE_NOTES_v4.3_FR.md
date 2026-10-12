# Notes de version — Virtual Lab Platform v4.3

**Objectif de la version :** rendre l'édition de la paillasse prévisible : ajout, modification, duplication, suppression, connexions, sauvegarde et restauration.

## Changements
- **Représentation canonique unique** (`serializeWorkspace`, `workspace_schema: 3`), utilisée à la fois par la sauvegarde du navigateur et par l'export JSON. Avant, il existait deux formats différents (`version: 4` et `schema_version: 2`).
- **Restauration validée** (`normalizeWorkspace`). Elle accepte les sauvegardes v4.0–v4.2 (`{version: 4, bench}`), les exports v2 et le schéma 3. Elle retire les éléments invalides, les identifiants dupliqués, les fils vers des composants ou des bornes inexistants et les fils en double. **Le nombre d'éléments retirés est affiché à l'utilisateur.**
- **Suppression complète** (`removeInstances`). Supprimer un contenant supprime aussi son contenu, de façon récursive, et **tous** les fils attachés à l'un d'eux. Avant, les fils d'un échantillon contenu restaient orphelins.
- **Valeurs invalides signalées.** Un champ vide ou non numérique n'est plus converti en 0 sans le dire. Le champ est marqué `aria-invalid`, une indication s'affiche, et le solveur refuse le calcul avec un message clair.
- **Duplication** d'un composant (bouton « Dupliquer ») : nouvelle instance, mêmes valeurs, aucun fil copié.
- **Marquage visible** « non calculé par le solveur CC » sur les composants électriques que le solveur ne calcule pas (condensateur, diode, transistor…).
- Suppression de trois anciennes versions mortes de `addItem`, `renderBench` et `renderInspector`. Elles étaient redéfinies plus loin dans le même bloc. J'ai vérifié que chaque ligne supprimée ne contenait que la fonction, sans autre instruction.

## Tests
- 8 nouveaux tests navigateur (`tests/browser/test_v43_workbench_integrity.py`). Exécutés contre l'interface v4.2, **6 échouent** : ce sont les nouveaux comportements. Les 2 autres (compatibilité des anciennes sauvegardes, vider la paillasse) étaient déjà corrects et servent de tests de non-régression.
- Tous les tests précédents passent ; voir `VALIDATION_MATRIX_v4.3.md`.

## Portée et limites
- **Annuler / rétablir n'existe pas.** C'est un choix documenté pour cette version : la suppression est immédiate. « Vider » demande une confirmation.
- Le déplacement d'un composant par glisser-déposer n'est pas couvert par les tests automatisés.
- Le serveur continue de valider lui-même les identifiants, les bornes et les valeurs. La validation dans l'interface ne remplace pas la sienne.

## Test ancien modifié (aucun supprimé)
- `test_v38_ui_reliability.py::test_workbench_can_explicitly_restore_saved_workspace` cherchait le texte `Array.isArray(saved.bench)`. Cette validation se trouve maintenant dans `normalizeWorkspace` (`Array.isArray(raw.bench)`) et elle est aussi testée dans un vrai navigateur.
