# Virtual Lab Platform v2.0

Application de recherche numérique locale (Python 3.10+), avec paillasse interactive, outils d'analyse scientifiques et nouveau solveur de circuits électriques résistifs en courant continu.

## Démarrage sur macOS
1. Décompresser le ZIP.
2. Ouvrir Terminal dans le dossier `virtual_lab_platform`.
3. Exécuter `sh launch_macos_linux.sh`.
4. Ouvrir `http://127.0.0.1:8765` dans le navigateur.
5. Laisser le Terminal ouvert pendant l'utilisation. Arrêter le serveur avec `Ctrl+C`.

## Tester les circuits
Dans la section **Laboratoire de circuits électriques / Electrical circuit laboratory** :
- choisissez une source idéale (par défaut 9 V) ;
- appliquez un montage en série ou en parallèle, ou modifiez les connexions entre nœuds ;
- saisissez les résistances en ohms ;
- cliquez sur « Résoudre le circuit / Solve circuit » ;
- examinez les tensions, courants, puissances et contrôles numériques ;
- exportez le résultat JSON.

Le nœud `S` est fixé à la tension de la source ; `0` est la masse. Les résistances sont linéaires et positives. Le réseau doit être électriquement connecté aux nœuds fixés, sinon le solveur signale un système singulier.

## Limites
Ce n'est pas un simulateur universel ni un remplacement de SPICE. Le nouveau moteur est limité au courant continu établi avec résistances idéales. Pas encore de circuits AC, transitoires, condensateurs, bobines, diodes ou transistors. Le copilote scientifique existant n'est pas une IA générative générale. Les modèles doivent être validés selon leurs domaines d'application avant toute utilisation réelle.
