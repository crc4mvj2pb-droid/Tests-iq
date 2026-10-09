# VirtuLab — plateforme de recherche scientifique virtuelle

Concevoir, exécuter et analyser des expériences numériques réalistes dans plusieurs disciplines, pour accélérer
les découvertes, réduire les coûts et ne garder pour le laboratoire que les essais de confirmation réellement utiles.

```bash
cd virtulab
npm install
npm run dev      # http://localhost:5173
npm test         # 59 tests : validations analytiques, statistiques, moteur
npm run build    # site statique dans dist/
```

## Fonctionnalités

| Étape | Ce que fait la plateforme |
|---|---|
| **Concevoir** | Choix du modèle, hypothèse, critère de succès quantitatif, objectif à optimiser, conditions nominales, estimation du nombre de simulations, du temps de calcul et du coût physique équivalent. |
| **Plans d'expériences** | Essai unique avec réplicats · balayage paramétrique (lin/log) · plan factoriel complet 2 facteurs · propagation d'incertitudes Monte Carlo (loi log-normale) · exploration par hypercube latin. |
| **Exécuter** | Calcul dans un Web Worker (interface fluide, barre de progression, annulation). Bruit de mesure instrumental optionnel. Graine aléatoire : chaque expérience est reproductible à l'identique. |
| **Analyser** | Test t unilatéral sur réplicats, IC 95 % (Student), probabilité de succès avec IC de Wilson, ANOVA à deux facteurs avec tests F, analyse de sensibilité (Spearman + coefficients de régression standardisés), optimum interpolé, meilleures configurations, distributions, cartes de réponse, faisceaux de trajectoires. |
| **Capitaliser** | Cahier de laboratoire (IndexedDB), notes, variantes, export CSV / JSON, import JSON avec ré-exécution, rapport imprimable PDF. |
| **Mesurer l'impact** | Essais physiques évités, coûts et temps de laboratoire économisés, essais de confirmation recommandés. |

## Modèles (7 disciplines, 13 validations analytiques)

| Discipline | Modèle | Méthode numérique | Validé contre |
|---|---|---|---|
| Physique | Balistique avec traînée quadratique et vent | RK4 + détection d'impact | Portée dans le vide, vitesse limite |
| Chimie | Réacteur fermé exothermique A→B→C, Arrhenius, emballement | Dormand-Prince 5(4) adaptatif | Solution de Bateman, ΔT adiabatique |
| Épidémiologie | SEIR + vaccination, mesures, hospitalisations | RK4 | Taille finale de Kermack-McKendrick, taux de croissance |
| Pharmacologie | PK orale à doses répétées, allométrie | Superposition exacte | AUC = F·D/CL, Cmax analytique |
| Ingénierie thermique | Paroi 1D, cycle jour/nuit | Différences finies implicites (Thomas) | Flux en régime permanent U·ΔT |
| Écologie | Rosenzweig-MacArthur avec prélèvement | Dormand-Prince 5(4) | Croissance logistique, équilibre N* |
| Bio-procédés | Bioréacteur Monod / Luedeking-Piret | Dormand-Prince 5(4) | S* du chémostat, bilan de masse batch |

La page **Vérification des modèles** ré-exécute toutes les validations dans le navigateur.

## Architecture

```
src/core/     intégrateurs ODE (RK4, RK45), statistiques, générateur aléatoire à graine
src/models/   un fichier par modèle : paramètres, indicateurs, simulation, cas de validation
src/engine/   plans d'expériences, exécution, worker, analyses, persistance, expériences types
src/ui/       DOM et graphiques SVG (courbes, histogrammes, cartes de chaleur, tornades)
src/views/    tableau de bord, concepteur, résultats, cahier, bibliothèque, vérification
tests/        Vitest
```

Aucune dépendance d'exécution : TypeScript + Vite uniquement. Tout le calcul est local.

## Limites assumées

- Les modèles sont des représentations établies mais simplifiées (hypothèses listées sur chaque fiche).
  Ils servent à cribler et prioriser ; les essais de confirmation physiques restent recommandés.
- Coûts physiques : ordres de grandeur indicatifs par discipline, à ajuster à votre contexte.
- Stockage local au navigateur (pas encore de compte multi-utilisateur ni de serveur).
- Ajouter une discipline = un fichier dans `src/models/` implémentant l'interface `Model`.
