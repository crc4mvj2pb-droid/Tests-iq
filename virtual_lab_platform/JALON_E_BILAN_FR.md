# Bilan du grand jalon E — « IA scientifique opérante » (v8.0 → v8.6)

**Porte de sortie (feuille de route) :** l'IA orchestre des tâches réelles sur des modèles validés et peut justifier toutes les valeurs présentées.

| Exigence | Preuve reproductible |
|---|---|
| Orchestration de tâches réelles | v8.0 : appels réels des contrats, du catalogue, de la maturité et des validations. v8.3 : graphe de tâches exécuté comme tâche de fond annulable, avec validation avant chaque exécution et limites. v8.5 : planification et recherche d'une cible, chaque proposition étant recontrôlée par une exécution du modèle. |
| Sur des modèles validés | Chaque réponse rappelle la maturité du modèle utilisé : tous sont « vérifiés », et Michaelis–Menten est « validé sur données ». v8.4 : la portée « modèle seulement » et ce qui manque pour conclure sur le système réel sont listés automatiquement. |
| Justifier toutes les valeurs | Chaque nombre renvoie à l'appel d'outil ou à la tâche qui l'a produit. Évaluation v8.6 : **0 % d'hallucination, traçabilité 100 %** sur 39 cas fixés à l'avance. En cas d'échec, de question hors périmètre ou inconnue, aucune valeur n'est donnée. |

**Évaluation :** la porte de sortie est franchie, avec une précision essentielle. L'« IA » livrée est un **assistant à règles, pas un modèle de langage**. Elle justifie ses valeurs parce qu'elle ne peut rien produire en dehors des outils. Sa compréhension du langage est limitée (36/39 sur le jeu d'évaluation, échecs publiés). Brancher un modèle de langage demanderait une nouvelle évaluation, impossible ici sans accès réseau ni clé.
