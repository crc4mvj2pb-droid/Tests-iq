# Feuille de route complète — Virtual Lab Platform

**Base de départ : v4.1 — 12 octobre 2026**  
**Objectif :** construire progressivement un laboratoire scientifique virtuel réellement utilisable, reproductible, validé et extensible.  
**Règle de pilotage :** avancer par grands jalons. Chaque « go » correspond à une étape concrète, avec livrable, tests et rapport. Ne pas confondre ajout de fonctionnalités et qualité scientifique.

---

## Principes non négociables

1. **Auditer avant de modifier.** Lire le code, reproduire les résultats et vérifier les affirmations des anciens rapports. Ne pas supposer que les fonctions sont opérationnelles parce qu'elles existent ou que les tests passent.
2. **Tester de bout en bout.** Une fonction importante doit être testée depuis l'interface jusqu'au résultat, à la sauvegarde et au rechargement. Les tests unitaires seuls ne suffisent pas.
3. **Ne pas simuler une validation.** Séparer clairement les résultats calculés, les mesures simulées et les données expérimentales réelles.
4. **Définir le périmètre des modèles.** Chaque solveur doit exposer les hypothèses, unités, plages valides, erreurs et limites. Refuser explicitement les configurations non prises en charge.
5. **Pas de chiffres inventés.** Les rapports de tests doivent être générés depuis les vraies commandes et les résultats observés. Indiquer les tests qui n'ont pas pu être exécutés.
6. **Préserver les versions.** Partir de la dernière version stable, garder une copie de la version précédente et produire un ZIP autonome propre.
7. **Pas d'IA qui masque l'absence de moteur.** L'IA scientifique viendra après l'existence de modèles fiables, d'API stables et de données traçables.
8. **Travailler par étapes.** Pour chaque grand jalon, définir l'étape suivante, l'implémenter, vérifier, documenter, livrer, puis s'arrêter en attendant « go ».

## État de départ v4.1

Fonctions présentes d'après le code et les documents du projet : serveur Python local, interface web dans `static/index.html`, solveur de circuit continu résistif depuis la paillasse, historique SQLite, calcul et vérification SHA-256 de la configuration canonique, rejeu d'un circuit sauvegardé, moteurs de cinétique chimique, stœchiométrie, instruments virtuels, analyses de données, protocoles et support SBML à différents niveaux.

Tests annoncés dans le rapport v4.1 : 170 tests réussis, compilation Python, vérification syntaxique des blocs JavaScript et test API d'un circuit 9 V / 1 kΩ. Limites explicites : pas de validation complète dans un navigateur réel ; rejeu limité au circuit CC résistif ; l'empreinte ne couvre pas l'intégralité du dossier ; le solveur de paillasse n'est pas SPICE.

Ces points constituent un **état à vérifier indépendamment**, pas une garantie préalable.

---

# GRAND JALON A — Terminer la v4 : laboratoire utilisable et reproductible

## v4.2 — Audit fonctionnel et tests navigateur

**But :** savoir précisément ce qui marche, ce qui casse et ce qui est seulement visuel.

Travail :
- Installer et lancer le projet dans un environnement propre avec la procédure documentée.
- Vérifier `/api/health`, `/api/version`, catalogue, unités, bibliothèque, modèles et historique.
- Mettre en place des tests navigateur reproductibles (Playwright si compatible, sinon outil disponible) et enregistrer les captures en cas d'échec.
- Parcours minimum : ouvrir l'application, ajouter un composant, sélectionner, modifier une valeur, connecter deux bornes, résoudre, lire le résultat, sauvegarder, ouvrir l'historique, vérifier l'empreinte, rejouer, recharger.
- Vérifier les erreurs réseau, les chargements, les messages d'erreur, les boutons désactivés, les double-clics et les soumissions répétées.
- Construire une matrice : fonctionnalité / étapes / résultat attendu / résultat observé / statut / preuve.

Critères de sortie :
- Aucun parcours critique n'est déclaré « testé » sans test automatisé ou preuve reproductible.
- Les défauts sont triés en bloquant, majeur, mineur et cosmétique.
- Le rapport distingue tests passés, échoués, ignorés et impossibles à lancer.

## v4.3 — État de paillasse et intégrité des connexions

**But :** rendre l'édition de la paillasse prévisible.

Travail :
- Vérifier l'ajout, la sélection, le déplacement, l'édition, la duplication et la suppression de composants.
- À la suppression d'un composant, supprimer ou signaler toutes ses connexions dépendantes.
- Empêcher les fils vers des instances ou bornes inexistantes.
- Empêcher les identifiants dupliqués, les valeurs numériques invalides et les bornes incompatibles.
- Définir une représentation canonique unique de l'état de la paillasse.
- Afficher distinctement les éléments présents, sélectionnés, reliés et non pris en charge par le solveur.
- Vérifier les opérations annuler/rétablir si elles existent ; sinon documenter la portée et envisager leur ajout.

Critères de sortie : aucune connexion orpheline après modification/suppression ; état sérialisé et restauré identique ; messages compréhensibles pour les erreurs courantes.

## v4.4 — Circuit continu : cohérence du solveur et diagnostic de topologie

**But :** sécuriser le seul périmètre déjà annoncé comme calculable.

Travail :
- Vérifier les valeurs (résistance strictement positive, source numérique finie, unités explicites).
- Tester circuit ouvert, résistance court-circuitée par un fil, source court-circuitée, masse manquante/double, branche flottante, composant isolé, résistance parallèle, série et réseau mixte.
- Détecter les nœuds flottants, résistances non raccordées et topologies singulières avant le calcul numérique.
- Vérifier loi des nœuds, loi des mailles lorsque applicable, conservation du courant et bilan de puissance avec tolérances documentées.
- Comparer à des solutions manuelles indépendantes et, si installable, à un solveur externe de référence comme ngspice ; ce dernier reste optionnel.
- Afficher courant, tension, puissance et nœuds avec unités et conventions de signe explicites.
- Garder les éléments reconnus mais non pris en charge comme tels : ne pas donner l'impression qu'une diode, un condensateur ou un transistor est calculé par le solveur DC.

Critères de sortie : cas de référence vérifiés indépendamment ; erreurs topologiques expliquées ; pas de résultat numérique trompeur sur une configuration invalide.

## v4.5 — Sauvegarde, restauration, export et migrations

**But :** préserver un projet complet entre deux sessions.

Travail :
- Définir un format JSON de projet versionné avec schéma, composants, connexions, paramètres, unités, métadonnées et versions du moteur.
- Ajouter export/import de projet et validation stricte avant chargement.
- Ajouter migrations explicites entre versions de schéma.
- Préserver l'ancien projet si un import échoue ; ne jamais remplacer l'état courant avant validation complète.
- Vérifier qu'un aller-retour sauvegarde → fermeture → rechargement produit le même état canonique et le même résultat numérique.
- Définir stratégie de sauvegarde SQLite, emplacement et comportement en cas de base absente ou corrompue.

Critères de sortie : tests aller-retour, migration et import malformé ; aucune perte silencieuse de données.

## v4.6 — Expérience chimique de bout en bout

**But :** faire une expérience chimique complète, sans prétendre que tous les modèles sont déjà disponibles.

Travail :
- Sélectionner un scénario simple réellement pris en charge, par exemple une réaction stœchiométrique connue.
- Faire circuler les entrées depuis l'interface vers l'API, valider les formules et unités, exécuter le calcul, présenter le réactif limitant et les quantités, puis enregistrer le protocole et le résultat.
- Vérifier les équations équilibrées, les unités mol/L/mol et les entrées manquantes.
- Relier les instruments virtuels uniquement si leur sortie est clairement marquée comme simulée.
- Tester les cas limites : formule inconnue, équation non équilibrée, quantité négative, quantité nulle, unité incompatible.
- Documenter la différence entre stœchiométrie idéale, cinétique et rendement expérimental.

Critères de sortie : un parcours chimique reproductible et traçable, et erreurs qui n'altèrent pas les quantités sauvegardées.

## v4.7 — Instruments et résultats traçables

**But :** relier les instruments virtuels aux résultats des moteurs, sans créer de fausses mesures.

Travail :
- Associer une grandeur simulée à un instrument compatible et à une unité.
- Enregistrer valeur modèle, lecture simulée, correction d'étalonnage, résolution, incertitude et graine aléatoire si utilisée.
- Empêcher les incompatibilités d'unité et de grandeur.
- Rendre les paramètres de simulation visibles et reproductibles.
- Ajouter la provenance du résultat : modèle, version, paramètres et horodatage.

Critères de sortie : aucune lecture n'est étiquetée « expérimentale réelle » sans source réelle explicitement identifiée.

## v4.8 — UX, accessibilité et diagnostics

Travail :
- Uniformiser les messages de succès, d'avertissement et d'erreur.
- Ajouter des états de chargement et empêcher les actions concurrentes dangereuses.
- Vérifier clavier, focus, labels, contrastes et affichage mobile/desktop.
- Ajouter journalisation locale avec identifiant de requête et erreurs exploitables, sans exposer de secrets.
- Réduire les erreurs JavaScript de console et traiter les réponses API inattendues.

Critères de sortie : parcours essentiels réalisables au clavier ; erreurs compréhensibles ; aucun échec critique de console sur les scénarios validés.

## v4.9 — Release candidate et audit de livraison

Travail :
- Lancer la suite complète depuis un environnement propre.
- Exécuter les tests navigateur et les tests API intégrés.
- Vérifier Windows et macOS/Linux selon les environnements réellement disponibles.
- Exclure caches, secrets, bases de développement et fichiers temporaires du ZIP.
- Vérifier que l'archive se décompresse et que le guide suffit à lancer le projet.
- Produire un rapport de test avec commandes exactes, versions des dépendances et limites.

Critères de sortie : tous les tests critiques passent ; aucune régression bloquante ; les limites sont écrites ; le paquet est autonome.

## v4.0 finalisée — porte de sortie vers v5

Ne déclarer la v4 « terminée » que si :
- les parcours de circuit et d'une expérience chimique sont testés de bout en bout ;
- la sauvegarde/restauration est validée ;
- les erreurs de topologie sont contrôlées ;
- le navigateur a été réellement utilisé dans des tests automatisés ou manuels documentés ;
- les résultats scientifiques sont séparés des données expérimentales ;
- la livraison est reproductible depuis un environnement propre.

---

# GRAND JALON B — v5 : moteurs scientifiques robustes et contrats communs

## v5.0 — Architecture du noyau scientifique
- Définir un contrat commun pour un modèle : identifiant, version, paramètres, unités, entrées, sorties, hypothèses, validité, erreurs, provenance et références.
- Standardiser la validation des paramètres et la structure des réponses API.
- Séparer interface, orchestration, calcul scientifique et persistance.
- Ajouter tests de contrats pour tous les moteurs existants.

## v5.1 — Quantités, unités et constantes
- Introduire un traitement systématique des unités et conversions.
- Détecter les dimensions incompatibles plutôt que convertir silencieusement.
- Versionner les constantes et conserver leur source/date de référence.
- Ajouter des tests dimensionnels aux équations principales.

## v5.2 — Calcul numérique, erreurs et convergence
- Définir tolérances, critères d'arrêt et gestion des erreurs numériques.
- Distinguer erreur de solveur, incertitude des paramètres et incertitude de mesure.
- Tester stabilité, convergence et cas limites.
- Ajouter diagnostics et messages en cas de non-convergence.

## v5.3 — Cinétique chimique validée
- Valider les modèles A→B et A→B→C sur solutions analytiques connues quand elles existent.
- Tester conservation de matière, positivité des concentrations et pas de temps.
- Comparer plusieurs pas de temps/intégrateurs et mesurer l'erreur.
- Documenter l'usage du solveur RK4 et ses limites.

## v5.4 — Circuits avancés vérifiés
- Étendre uniquement après validation du circuit DC : transitoires RC/RL, puis RLC et AC selon les solveurs disponibles.
- Comparer chaque modèle à des cas analytiques et/ou solveurs de référence.
- Ajouter graphiques tension/courant/puissance et unités cohérentes.
- Ne pas prétendre simuler des composants non linéaires sans modèle approprié.

## v5.5 — Balayages, sensibilité et incertitude
- Rendre les balayages paramétriques robustes, annulables et exportables.
- Séparer variation de paramètre, incertitude instrumentale et incertitude de modèle.
- Vérifier graines aléatoires, reproductibilité et intervalles de résultats.
- Éviter d'interpréter une corrélation ou un fit comme une preuve causale.

## v5.6 — SBML et modèles importés
- Vérifier la prise en charge SBML réellement implémentée et signaler les éléments non pris en charge.
- Valider les unités, paramètres, espèces, réactions et conditions initiales importés.
- Préserver le fichier source et la provenance du modèle.
- Ajouter tests sur fichiers valides, invalides et fonctionnalités SBML inconnues.

## v5.7 — Qualité des modèles et catalogue honnête
- Attribuer des niveaux de maturité : maquette conceptuelle, modèle calculable, modèle vérifié, modèle validé sur données.
- Pour chaque modèle, exposer équations, hypothèses, limites, jeux de référence et état de validation.
- Retirer les affirmations non justifiées par le code.

## v5.8 — Expériences multi-modèles
- Définir des adaptateurs entre modèles avec unités et conversions explicites.
- Créer une expérience combinant au moins deux moteurs validés.
- Détecter incompatibilités de variables, échelles temporelles et conditions aux limites.
- Conserver les sorties intermédiaires et la provenance de chaque étape.

## v5.9 — Benchmark scientifique indépendant
- Construire des jeux de cas de référence séparés des tests unitaires.
- Comparer les sorties aux valeurs analytiques, publications ou logiciels de référence lorsque les licences et données le permettent.
- Documenter les écarts, critères d'acceptation et résultats négatifs.

**Porte de sortie v5 :** au moins plusieurs moteurs sont validés sur des références indépendantes, les unités et contrats sont cohérents, et les expériences multi-modèles ne masquent pas les limites de chaque moteur.

---

# GRAND JALON C — v6 : données, provenance et validation scientifique

## v6.0 — Catalogue de données versionné
- Schéma commun pour propriété, valeur, unité, température/pression/conditions, source, date, licence, incertitude et domaine d'applicabilité.
- Séparer données importées, données calculées, données simulées et données expérimentales.
- Ajouter recherche, filtres, validation et export.

## v6.1 — Sources et références
- Référencer chaque constante et paramètre de modèle.
- Stocker la version et les métadonnées de la source.
- Ne jamais présenter une valeur approximative sans l'étiqueter.

## v6.2 — Import et qualité des données
- Import CSV/JSON avec aperçu, détection des unités et validation de schéma.
- Rapporter valeurs manquantes, doublons, valeurs aberrantes et transformations appliquées.
- Garder le fichier d'origine inchangé.

## v6.3 — Analyse et ajustement de modèles
- Régression avec hypothèses, métriques, résidus et diagnostics.
- Séparer données d'ajustement et de validation.
- Afficher les limites de l'extrapolation.

## v6.4 — Traçabilité complète
- Journal d'événements de l'expérience : modèle et version, paramètres, fichiers sources, graines, résultats, erreurs et environnement logiciel.
- Calcul d'empreinte sur un manifeste complet et clairement défini ; ne pas appeler cela preuve d'authenticité externe.
- Export d'un paquet reproductible avec manifest et rapport.

## v6.5 — Rapports scientifiques
- Générer rapport de méthode, paramètres, résultats, unités, graphiques, incertitudes, hypothèses et limites.
- Citer les sources utilisées et conserver les données de base.
- Distinguer observations, calculs, interprétations et conclusions.

**Porte de sortie v6 :** un tiers peut récupérer un dossier d'expérience et reproduire le calcul dans un environnement documenté.

---

# GRAND JALON D — v7 : élargissement disciplinaire par modules validés

Ne pas développer tous les domaines simultanément. Sélectionner un domaine, définir un modèle limité et le valider avant d'en ajouter un autre.

## v7.0 — Architecture des domaines
- Interfaces communes pour unités, solveurs, jeux de données, paramètres et visualisations.
- Catalogue avec niveaux de maturité visibles.

## v7.1 — Thermique et transferts
- Commencer par bilans énergétiques simples, capacités thermiques et systèmes à constantes de temps.
- Valider sur solutions analytiques et cas documentés.

## v7.2 — Chimie physicochimique
- Étendre progressivement équilibre ou thermodynamique avec données sourcées.
- Définir clairement les hypothèses et domaines de validité.

## v7.3 — Biologie quantitative
- Modèles simples de croissance, réactions enzymatiques ou populations.
- Contrôler conservation, unités, paramètres et validation sur données publiques.

## v7.4 — Neurosciences computationnelles
- Commencer par modèles mathématiques classiques et bien délimités.
- Ne pas présenter ces modèles comme des jumeaux complets du cerveau humain.

## v7.5 — Modèles biomédicaux exploratoires
- Éventuels modèles de croissance tumorale ou de mécanismes associés à des maladies, uniquement si les équations, données et limites sont justifiées.
- Positionner les résultats comme exploratoires et non comme conseils médicaux ni prédictions cliniques validées.

## v7.6 — Comparaison interdisciplinaire
- Relier deux ou plusieurs modèles au moyen d'adaptateurs testés.
- Montrer l'effet de chaque hypothèse et les incertitudes propagées.

**Porte de sortie v7 :** chaque module ajouté a un périmètre limité, un benchmark et un statut de validation explicite.

---

# GRAND JALON E — v8 : IA scientifique opérante

## v8.0 — Assistant connecté aux outils, pas seulement conversationnel
- L'IA doit appeler les modèles et outils réels via des interfaces contrôlées.
- Afficher les appels, paramètres, sorties, erreurs et sources.
- Ne pas inventer de résultats si un moteur échoue.

## v8.1 — Question de recherche et hypothèses
- Transformer une question en variables, hypothèses testables et critères d'évaluation.
- Demander des clarifications lorsque les données ou objectifs manquent.

## v8.2 — Conception de protocoles
- Proposer matériel virtuel, paramètres, contrôles et répétitions.
- Vérifier que chaque étape est compatible avec les moteurs disponibles.
- Signaler les hypothèses et éléments non simulés.

## v8.3 — Exécution planifiée et sûre
- Exécuter les étapes dans un graphe de tâches traçable.
- Valider les entrées avant chaque étape ; limites de temps et de ressources.
- Annulation réelle des tâches lorsque possible, sinon signaler honnêtement ce qui continue en arrière-plan.

## v8.4 — Analyse critique
- Comparer hypothèses et résultats, afficher incertitudes et sensibilité.
- Séparer résultat calculé, interprétation du modèle et explication générée par l'IA.
- Identifier les données manquantes et les limites qui empêchent une conclusion.

## v8.5 — Planification itérative
- Proposer l'expérience suivante en fonction d'un objectif explicite.
- Optimiser des paramètres sous contraintes connues ; expliquer le critère d'optimisation.
- Comparer plusieurs plans et conserver la décision de l'utilisateur.

## v8.6 — Évaluation de l'IA
- Construire un jeu d'évaluation avec réponses attendues, erreurs scientifiques, hallucinations, appels d'outils et traçabilité.
- Mesurer les taux d'erreur ; tester les cas où la bonne réponse est « inconnu ».
- Aucune affirmation d'autonomie scientifique générale sans preuves d'évaluation.

**Porte de sortie v8 :** l'IA orchestre des tâches réelles sur des modèles validés et peut justifier toutes les valeurs présentées.

---

# GRAND JALON F — v9 : collaboration et déploiement

- Projets, utilisateurs et rôles si une collaboration multi-utilisateur devient nécessaire.
- Historique, sauvegardes, import/export et partage de dossiers reproductibles.
- Architecture de déploiement, configuration, gestion des dépendances et migrations.
- Sécurité des entrées, limites de ressources, isolation des imports et protection des données.
- Observabilité, diagnostics et récupération après panne.
- Documentation, installation, mises à jour et procédure de support.
- Évaluation de charge seulement après définition du nombre d'utilisateurs et du type de calcul attendu.

**Porte de sortie v9 :** application installable et maintenable, avec pratiques de sécurité et de sauvegarde adaptées au mode de déploiement visé.

---

## Routine obligatoire pour chaque « go »

1. Partir de la dernière archive et confirmer son contenu.
2. Lire les modules concernés et comprendre les contrats existants.
3. Écrire des critères d'acceptation avant le code.
4. Implémenter une tranche cohérente, sans refonte gratuite.
5. Ajouter tests unitaires, API et navigateur selon le parcours.
6. Lancer les tests réellement disponibles et consigner les commandes.
7. Tester au moins un cas nominal et plusieurs cas d'erreur.
8. Vérifier qu'aucune donnée d'expérience n'est corrompue par une erreur.
9. Mettre à jour version, README, guide, notes et rapport.
10. Créer un ZIP propre, vérifier son intégrité et tester l'installation autant que possible.
11. Fournir liens, changements, tests passés/échoués/non exécutés et limites restantes.
12. S'arrêter et attendre le prochain « go ».

## Définition d'une étape « terminée »

Une étape n'est terminée que si le code, les tests, les documents et le paquet correspondent. Un nombre de tests réussis ne remplace pas les tests de parcours utilisateur ni la validation scientifique. Toute fonction non testée dans un navigateur doit être annoncée comme telle.
