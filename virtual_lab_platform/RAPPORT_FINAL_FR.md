# Rapport final — Virtual Lab Platform v9.4

Ce rapport couvre tout le travail réalisé depuis l'audit de la v4.1, selon la feuille de route `docs/ROADMAP_VIRTUAL_LAB_PLATFORM_FR.md`.

**Méthode suivie pour chaque version :**
1. critères d'acceptation écrits avant le code ;
2. implémentation sans refonte gratuite ;
3. tests unitaires, d'API et en navigateur réel ;
4. validation complète générée (`scripts/run_validation.py`), qui **bloque la publication au moindre échec** ;
5. archive ZIP avec manifeste SHA-256, vérifiée dans un dossier propre ;
6. commit et envoi.

Les chiffres ci-dessous proviennent tous de fichiers générés : matrices de validation, rapports de banc d'essai et d'évaluation.

## Versions livrées

| Jalon | Versions | Tests réussis à la fin du jalon | Porte de sortie |
|---|---|---|---|
| A — laboratoire utilisable | v4.2 → v4.9 | 600 | franchie (`JALON_A_BILAN_FR.md`) |
| B — moteurs robustes et contrats | v5.0 → v5.9 | 920 | franchie (`JALON_B_BILAN_FR.md`) |
| C — données, provenance, validation | v6.0 → v6.5 | 1 005 | franchie : un tiers reproduit un calcul depuis un paquet, en processus isolé (`JALON_C_BILAN_FR.md`) |
| D — domaines validés | v7.0 → v7.6 | 1 088 | franchie (`JALON_D_BILAN_FR.md`) |
| E — IA opérante | v8.0 → v8.6 | 1 156 | franchie, avec un assistant **à règles** (`JALON_E_BILAN_FR.md`) |
| F — déploiement | v9.0 → v9.4 | voir `VALIDATION_MATRIX_v9.4.md` | franchie pour un usage local mono-utilisateur (`JALON_F_BILAN_FR.md`) |

Le nombre de tests est passé de 170 (v4.1) à plus de 1 190, **sans aucun test supprimé**. Les tests anciens adaptés (8 cas, chacun lié à un changement voulu et documenté dans les notes de version) sont listés dans les notes concernées.

## État final, mesuré

- **27 contrats de modèles** (paramètres typés avec unités et bornes, sorties avec unités, références) répartis dans **8 domaines**. Chaque domaine a un périmètre, des exclusions et au moins un cas de référence indépendant.
- **Maturité vérifiée par la machine** : 29 modèles vérifiés, **1 validé sur données réelles** (Michaelis–Menten sur la Puromycine, protocole fixé à l'avance, témoin négatif rejeté), 1 calculable, 33 maquettes conceptuelles. Chaque niveau cite des tests qui doivent réussir.
- **Banc d'essai indépendant** : 43 cas (références analytiques, publiées et solveurs indépendants), tous conformes. Il comprend 4 résultats négatifs documentés et 3 incidents consignés, dont 2 où **c'est ma propre référence qui était fausse**.
- **Données** : catalogue sourcé (Puromycine, DBO, pKa, constantes SI et CODATA) avec verrou de version ; bibliographie de 45 sources sans orpheline.
- **Ajustement** : estimations publiées de Bates & Watts reproduites exactement.
- **Traçabilité** : dossiers vérifiables, rejeu, journal, paquets reproductibles relancés par un tiers, rapports qui séparent observations, calculs, interprétation et conclusions.
- **Assistant** : 36/39 sur un jeu d'évaluation fixé à l'avance, **0 % d'hallucination, traçabilité 100 %**. Les échecs sont publiés sans être ajustés.
- **Installation** : seule la bibliothèque standard est nécessaire ; 12 contrôles d'installation ; sauvegardes et restauration sûres ; mode récupération ; sécurité adaptée à un usage local.

## Défauts réels trouvés et corrigés au fil des versions (sélection)

- Double soumission dans l'interface ; message de rejeu invisible ; empreinte cassée par la sérialisation JavaScript (v4.x).
- Règles SBML ignorées en silence ; paramètres locaux et globaux mélangés (v5.6).
- Estimation d'erreur nulle de Dormand–Prince ; unité de concentration absente des dossiers (v5.x).
- Nombre de modèles annoncé faux (« 30 » au lieu de 33) (v5.7).
- Température par défaut incohérente dans une chaîne multi-modèles (v5.9).
- Maquette homonyme d'un modèle calculable (v7.2).
- `NaN` et `Infinity` acceptés dans le JSON ; contrôle DTD du SBML contournable (v9.1).

## Limites restantes (à connaître avant tout usage)

1. **Validation sur données** : un seul modèle est validé sur des mesures réelles. Les autres résolvent correctement leurs équations, ce qui ne prouve pas qu'ils décrivent la réalité.
2. **Références** : les sources bibliographiques et les pKa ont été saisis d'après des références connues, mais **n'ont pas pu être relus dans les publications originales** depuis cet environnement. Une relecture par une personne qui y a accès est recommandée.
3. **Assistant** : ce n'est pas un modèle de langage. Sa compréhension repose sur des mots-clés : il répond « inconnu » plus souvent qu'il ne se trompe. Le critère H0 (sensibilité normalisée) est trompeur pour des grandeurs à zéro décalé, comme une température en kelvins (échec `hypothesis_3` publié).
4. **Électricité** : pas de composants non linéaires, pas de SPICE.
5. **Plateformes** : contrôlé sous Linux, avec Chromium et Python 3.10 à 3.14. **Windows, macOS, Safari et Firefox n'ont pas été essayés.** Un essai sur votre Mac est recommandé (`python scripts/install_check.py`).
6. **Usage** : local et mono-utilisateur, sans authentification. Ne pas exposer le serveur sur un réseau. Aucun usage clinique.

## Pour vérifier vous-même

```
python scripts/verify_manifest.py        # intégrité de l'archive
python scripts/install_check.py          # 12 contrôles de l'installation
python scripts/run_benchmarks.py         # banc d'essai indépendant
python scripts/run_assistant_eval.py     # évaluation de l'assistant
python scripts/run_validation.py         # tous les tests (développeurs, voir INSTALLATION_FR.md)
```
