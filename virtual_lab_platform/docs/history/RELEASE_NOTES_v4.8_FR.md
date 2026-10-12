# Notes de version — Virtual Lab Platform v4.8

**Objectif de la version :** traiter les erreurs, les chargements, le clavier, l'accessibilité et les erreurs de console, et sécuriser le serveur local (problème n° 9 de l'audit).

## Sécurité du serveur local
- **`Host` étranger refusé (403).** Une page qui fait pointer son propre domaine vers 127.0.0.1 (*DNS rebinding*) ne peut plus lire l'API.
- **`Origin` étrangère refusée (403).** Un site tiers ne peut plus écrire dans l'historique ni importer de fichiers par une requête « simple » (CSRF). L'audit v4.1 avait montré qu'une telle requête était acceptée.
- Sont acceptés `127.0.0.1`, `localhost` et `[::1]` sur le port du serveur. Une requête sans en-tête `Origin` (curl, scripts locaux) reste acceptée.
- 14 tests couvrent les hôtes locaux et étrangers, les origines locales, étrangères, `null`, `https` et les autres ports.

## Erreurs et chargements
- **Gestion centrale des erreurs réseau.** Pour tous les panneaux, un serveur injoignable donne « Le serveur local est injoignable… ». Une réponse non JSON donne « Réponse inattendue du serveur local (HTTP n) » au lieu d'une erreur d'analyse JSON.
- **Protection contre la double soumission** sur 14 boutons de calcul : bouton désactivé, `aria-busy`. La protection fonctionne même quand un panneau attache son action après le chargement de son catalogue. **Défaut trouvé par le test navigateur :** un double-clic sur « Run » du concepteur créait 2 dossiers.

## Accessibilité (audit axe-core 4.10.2, fourni dans `tests/browser/vendor/` avec sa licence MPL-2.0)
- Au départ : 2 types de violations **critiques** (13 champs de protocole sans nom accessible), 2 types **sérieux** (dont **40 éléments au contraste insuffisant**), 2 modérés et 1 mineur.
- **Défaut de lisibilité réel corrigé.** Les libellés des panneaux Cinétique, Réaction, Instruments et Copilote étaient presque invisibles (gris #c2d0e3 sur blanc, contraste 1,56 au lieu de 4,5). C'était un reste du thème sombre.
- Les champs ont des noms accessibles. Les schémas ont `role="img"`. Les sections et les panneaux sont des régions nommées. L'en-tête de tableau vide a un libellé pour les lecteurs d'écran.
- **Résultat : 0 violation au chargement**, et 0 violation critique ou sérieuse après l'affichage de résultats (circuit et cinétique). Le contenu ajouté dynamiquement (inspecteur de la paillasse) a aussi été corrigé.
- `python scripts/accessibility_audit.py [--contrast]` refait l'audit à la demande.

## Clavier et console
- **Parcours au clavier seul** (Tab + Entrée) : ajouter, sélectionner, saisir les valeurs, câbler et résoudre le circuit de référence. Testé dans Chromium, I = 9 mA.
- **Aucune erreur de console** lors des actions par défaut de 6 panneaux : modèle, cinétique, réaction, suite de validation, instrument, historique.

## Limites
- L'audit automatique ne remplace pas un test avec un lecteur d'écran réel (VoiceOver, NVDA) ni un avis d'utilisateurs. Ces tests n'ont pas été faits.
- Les violations modérées liées aux zones de contenu dynamique ne sont vérifiées que pour les panneaux testés.
- Le contrôle `Origin`/`Host` protège contre les pages web. Il ne protège pas contre un programme malveillant déjà installé sur l'ordinateur.
