# Virtual Lab Platform

**Laboratoire scientifique virtuel local, multidisciplinaire, traçable et honnête sur ses limites.** L'application tourne sur votre ordinateur (Python 3.10 ou plus récent, aucune bibliothèque tierce), dans votre navigateur, à l'adresse http://127.0.0.1:8765. Les résultats calculés sont des **simulations, pas des mesures**.

## Démarrer
- macOS / Linux : `sh launch_macos_linux.sh` · Windows : `launch_windows.bat` · partout : `python app.py`
- Guide d'utilisation : **`GUIDE_UTILISATEUR_FR.md`** · Installation, sauvegardes, mises à jour, support : **`GUIDE_ADMINISTRATION_FR.md`** et `INSTALLATION_FR.md`
- Vérifier une installation : `python scripts/install_check.py`

## Ce que fait la plateforme
| Domaine | Ce qui est réellement calculé |
|---|---|
| Électricité | Réseaux résistifs CC (paillasse graphique), transitoires RC/RL, RLC série (échelon, sinusoïdal, balayage) |
| Chimie | Cinétique d'action de masse (3 intégrateurs dont un pour systèmes raides), stœchiométrie, Arrhenius, équilibres acide–base exacts et titrages |
| Thermique | Corps à une capacité thermique (contrôle de Biot), murs composites, diffusion 1D |
| Biologie | Michaelis–Menten (**validé sur données publiques**), croissance logistique, Lotka–Volterra |
| Neurosciences | Intègre-et-tire, Hodgkin–Huxley (1952), FitzHugh–Nagumo |
| Biomédical exploratoire | SIR, pharmacocinétique, Gompertz, Finke–Watzky — jamais à usage clinique |
| Données | Catalogue sourcé, import CSV/JSON avec contrôle qualité, ajustement non linéaire avec diagnostics et validation séparée |
| Traçabilité | Dossiers vérifiables, rejeu, journal, paquets reproductibles (un tiers relance le calcul), rapports scientifiques |
| Assistant | À règles (pas un modèle de langage) : appels d'outils tracés, aucune valeur inventée, évaluation publiée |
| Maintenance | Configuration validée, sauvegardes et restauration, diagnostic, mode récupération, projets partageables |

Chaque modèle porte un **niveau de maturité vérifié par la machine** (maquette, calculable, vérifié, validé sur données) avec ses preuves. Voir `GET /api/maturity`, le rapport `BENCHMARK_REPORT_FR.md` (banc d'essai indépendant) et `ASSISTANT_EVAL_REPORT_FR.md`.

## Ce qu'elle ne fait pas
Pas de SPICE ni de composants non linéaires ; pas de modèle de langage ; pas de collaboration multi-utilisateur ; aucune prédiction clinique ; un seul modèle validé sur données réelles (les autres sont vérifiés mathématiquement). Ne pas exposer le serveur sur un réseau.

## Où trouver quoi
- Notes de la version courante : `RELEASE_NOTES_v<version>_FR.md` ; matrice de validation générée : `VALIDATION_MATRIX_v<version>.md`
- Bilans des grands jalons : `JALON_A_BILAN_FR.md` … `JALON_F_BILAN_FR.md` ; rapport final : `RAPPORT_FINAL_FR.md`
- Architecture : `ARCHITECTURE_FR.md` ; historique des versions : `docs/history/` ; feuille de route : `docs/ROADMAP_VIRTUAL_LAB_PLATFORM_FR.md`
