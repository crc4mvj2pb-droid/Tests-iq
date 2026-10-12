# Virtual Lab Platform v2.2

## Correctifs principaux

- Isolation du script de la paillasse : une erreur d’initialisation dans les anciens outils ne doit plus empêcher le chargement des interactions de la paillasse.
- Catégorie « Électricité & électronique » ajoutée au catalogue avec source CC, résistance, condensateur, inductance et fiches clairement marquées pour les composants qui ne sont pas encore simulés.
- Les objets électriques déposés sur la paillasse orientent vers le solveur électrique dédié plutôt que de prétendre calculer un circuit à partir de simples cartes.
- Le bouton « Outils de recherche avancés » mène directement aux outils de recherche.
- Conservation des solveurs électriques CC, RC/RL et RLC disponibles dans cette version, avec leurs limites documentées.

## Démarrage sur macOS

1. Décompresser l’archive dans un nouveau dossier.
2. Ouvrir Terminal dans ce dossier.
3. Exécuter `sh launch_macos_linux.sh`.
4. Ouvrir `http://127.0.0.1:8765`.
5. Garder le Terminal ouvert. Si une autre version utilise déjà le port, l’arrêter avec `Ctrl+C` avant de lancer celle-ci.

## Limites

Les composants électriques sont des fiches de catalogue ; seuls les solveurs explicitement décrits dans l’interface effectuent des calculs. Le solveur DC couvre des réseaux résistifs linéaires idéalisés. Les modèles RC/RL et RLC sont analytiques et idéalisés, pas un moteur SPICE généraliste. La catégorie électrique ne constitue pas une simulation de diodes ou de transistors. La bibliothèque biologique et moléculaire contient encore des représentations conceptuelles.

## Vérification

Suite logicielle héritée : 97 tests automatisés réussis. Compilation Python et syntaxe JavaScript vérifiées. Cette livraison n’a pas été testée dans une session réelle de Safari sur le Mac de l’utilisateur ; elle doit être ouverte et vérifiée localement.
