# Notes de version — Virtual Lab Platform v6.5

**Objectif (feuille de route) :**
- générer un rapport : méthode, paramètres, résultats, unités, graphiques, incertitudes, hypothèses et limites ;
- citer les sources utilisées et conserver les données de base ;
- distinguer observations, calculs, interprétations et conclusions.

## Critères d'acceptation (fixés avant le code) et résultat

| Critère | Résultat |
|---|---|
| Contenu complet | `reports.py` construit le rapport **uniquement** à partir du dossier enregistré, du contrat du modèle, du catalogue, de la bibliographie et du journal. Il compte 11 sections dans un ordre fixe : question et objet ; méthode (moteur et version, équations, validité, maturité) ; paramètres (avec unités, valeurs par défaut marquées « illustratives ») ; observations ; calculs ; incertitudes ; hypothèses et limites ; interprétation ; conclusions ; références ; traçabilité (empreintes, journal). |
| Quatre natures d'énoncés séparées | **Observations** : seulement des données mesurées ou importées, avec leur nature et leur sous-ensemble ; sinon, « aucune donnée observée ». **Calculs** : valeurs du moteur avec unités et erreurs types. **Interprétation** : phrases produites par des règles fixes à partir des contrôles (contrôles internes, validation séparée, test des suites), annoncées comme telles. **Conclusions** : « À rédiger par le chercheur ». La plateforme ne formule pas de conclusion scientifique. |
| Rien d'inventé | Un test vérifie que **chaque nombre de la section « Calculs » figure dans le dossier**. |
| Sources citées | Références complètes tirées de la bibliographie v6.1 : celles du modèle, plus celles des données. Pour un ajustement : Bates & Watts, la forme du modèle (par exemple Michaelis & Menten 1913) et les sources du jeu de données (Treloar 1974…). |
| Données de base et graphiques | Le rapport existe en Markdown (tableau des données du graphique) et en HTML **autonome** : graphique SVG intégré, tableau des données, ni script ni ressource externe (test). |
| Accès | `GET /api/history/{id}/report.md` et `/report.html`. Liens « Rapport » et « Paquet reproductible » sur chaque expérience de l'historique (test en navigateur). |

## Tests
- `tests/test_v65_reports.py` : 6 tests.
- `tests/browser/test_v65_report_ui.py` : 1 test en navigateur réel.

## Limites
- Les phrases d'interprétation sont des règles simples. Elles signalent, elles n'expliquent pas. Leur portée est rappelée en tête de section.
- Le graphique montre au plus 4 séries et le tableau HTML au plus 500 lignes. Le dossier JSON reste la référence complète.
