# Guide de recherche — Virtual Lab Platform v1.7

## Démarrer
- Windows : lancer `launch_windows.bat`.
- macOS/Linux : `sh launch_macos_linux.sh`.
- Ou exécuter `python app.py`, puis ouvrir `http://127.0.0.1:8765`.
- Python 3.10+ requis ; aucune dépendance Python tierce n'est nécessaire.

## Lancer un modèle
Dans **Experiment designer**, sélectionner un modèle et régler ses paramètres. Cliquer sur **Run experiment**. Les résultats contiennent un résumé, des lignes calculées, des contrôles numériques et des limites. Exporter le dossier JSON pour conserver la configuration et les résultats.

## Nouveaux modèles v1.7
- **Logistic population growth** : croissance d'une population limitée par une capacité de charge.
- **First-order reaction A → B** : conversion analytique avec conservation de A+B.
- **First-order environmental decay** : diminution d'une charge dans un compartiment unique.
- **One-compartment concentration decay** : exemple pédagogique de concentration qui décroît ; pas un outil de prescription ou de choix de dose.
- **Lotka–Volterra** : dynamique proie-prédateur avec intégrateur RK4.
- **Leaky integrate-and-fire neuron** : modèle neuronal très simplifié avec seuil et réinitialisation.
- **Arrhenius reaction** : influence de la température sur une constante cinétique, à température constante.

## Outils de recherche génériques
Les panneaux **General research analysis** et **Compare any model output** utilisent le modèle sélectionné dans le formulaire principal.

- **Parameter sweep** : choisir un paramètre numérique, saisir 2 à 25 valeurs distinctes et, si nécessaire, un champ numérique du résumé. Sans champ explicite, la plateforme choisit une sortie de résumé par défaut pour le modèle.
- **Monte Carlo uncertainty** : choisir un paramètre, son écart-type supposé, le nombre d'échantillons (30–2000) et le champ numérique à analyser. Les paramètres sont échantillonnés indépendamment selon une loi normale. La graine fixe rend le résultat reproductible. Les échantillons invalides sont rejetés.
- **Reference comparison** : saisir un CSV `x,y`, puis indiquer les colonnes du modèle correspondant à x et y. Les métriques (MAE, RMSE, biais) ne sont calculées que sur la plage de référence ; aucune extrapolation n'est faite.

## API de recherche
- `GET /api/research/roadmap` : feuille de route des dix axes et état réel de chacun.
- `POST /api/research/sweep` : balayage générique d'un paramètre.
- `POST /api/research/uncertainty` : propagation Monte Carlo générique.
- `POST /api/research/compare` : comparaison de colonnes de sortie à des données de référence fournies.

## Interpréter les résultats correctement
Tous les nouveaux modèles sont au niveau **L1** : calcul numérique et contrôles logiciels de base. Cela n'est pas une validation expérimentale. Les paramètres sont illustratifs à moins que tu ne les remplaces par des valeurs sourcées et vérifiées. Les sources listées dans le catalogue sont des pointeurs bibliographiques ; aucun jeu de données externe n'a été téléchargé ou validé dans cette version.

Le modèle pharmacocinétique est pédagogique uniquement. La plateforme ne réalise pas de diagnostic, ne recommande pas de traitement, ne certifie pas la sécurité cosmétique et ne remplace pas les analyses physiques ou biologiques. Les modèles spécifiques du cancer et d'Alzheimer, un modèle cosmétique validé, le contrôle matériel réel, la conformité SBML complète et l'IA scientifique restent à développer.
