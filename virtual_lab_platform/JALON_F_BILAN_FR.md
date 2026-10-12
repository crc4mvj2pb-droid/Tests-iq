# Bilan du grand jalon F — « Collaboration et déploiement » (v9.0 → v9.4)

**Porte de sortie (feuille de route) :** une application installable et maintenable, avec des pratiques de sécurité et de sauvegarde adaptées au mode de déploiement visé.

**Mode de déploiement visé :** application **locale et mono-utilisateur**, sur l'ordinateur du chercheur, sans exposition réseau.

| Exigence | Preuve reproductible |
|---|---|
| Installable | Seule la bibliothèque standard est nécessaire. Lanceurs macOS/Linux et Windows. `scripts/install_check.py` démarre le vrai serveur avec des données temporaires et réussit 12 contrôles (`tests/test_v94_install_check.py`). Essai en dossier propre sur plusieurs versions de Python : `RC_CHECK_v9.4_FR.md`. |
| Maintenable | Configuration validée qui refuse de démarrer si elle est invalide (v9.0). Migrations automatiques avec copie de sécurité (depuis v4.5). Journal et diagnostic (v9.2). Guides utilisateur et administrateur, avec procédure de support (v9.4). |
| Sauvegardes | Copies cohérentes, vérifiées et atomiques ; sauvegarde automatique au démarrage ; restauration sûre qui conserve l'état précédent (v9.0, v9.2). |
| Sécurité adaptée | Écoute locale uniquement, contrôle Host/Origin (v4.8), CSP et en-têtes de sécurité, limites de taille, de profondeur et de débit, imports isolés ; deux défauts réels corrigés (v9.1). |
| Récupération après panne | Mode récupération en lecture seule si la base est endommagée, vérifié en processus séparé (v9.2). |
| Partage | Projets exportés en ZIP vérifiable, avec paquets reproductibles (v9.3). |

**Choix assumés :**
- pas de comptes ni de rôles, faute de besoin multi-utilisateur établi ;
- pas d'évaluation de charge au-delà d'une mesure mono-utilisateur (médiane d'environ 1 ms par requête simple), conformément à la feuille de route : « seulement après définition du nombre d'utilisateurs ».

**Évaluation :** la porte de sortie est franchie pour ce mode de déploiement. Windows, macOS, Safari et Firefox n'ont pas pu être essayés ici.
