# FlipRush

Jeu de course arcade 2D à physique — inspiré de la philosophie de *Rider* (accélération/rotation en vol, flips, atterrissages précis) mais avec son propre univers, ses propres voitures, ses propres circuits et son propre système de progression. Aucun asset, niveau, logo ou contenu de Rider n'a été copié : identité visuelle, noms, voitures et environnements sont originaux.

**Nom du jeu : FlipRush.** Autres pistes envisagées si tu préfères en changer (c'est une simple constante à éditer, voir `client/index.html` et `client/src/style.css`) : *Turbo Loop*, *Driftwave*, *Aeroflip*, *Loopline*.

## Ce qui est réellement fonctionnel aujourd'hui

Tout ce qui suit est **implémenté et jouable**, pas simulé :

- **Moteur physique réel** (Matter.js) : voiture à châssis + 2 roues motrices sur suspensions, gravité, inertie, friction, collisions, rebonds. Tenir le bouton accélère et fait tourner le nez en l'air ; relâcher laisse la physique reprendre la main.
- **Solo** : 20 niveaux, difficulté croissante (faciles 1-5, intermédiaires 6-10, difficiles 11-15, extrêmes 16-20), checkpoints avec crash → réanimation (3-2-1-GO) → reprise au dernier checkpoint sans réinitialiser le chrono, 3 paliers d'étoiles par niveau, sauvegarde locale des meilleurs temps.
- **Classic** : circuit procédural infini, généré par chunks au fur et à mesure (jamais deux parties identiques), **59 obstacles/éléments** catalogués (rampes, gaps, plateformes mobiles/rotatives/qui tombent, tunnels, loops, murs/barrières, sections techniques...) combinés en patterns nommés (FLIP, SPEED, TECHNIQUE, CHAOS, EXPERT) avec une difficulté qui augmente par palier de distance (0-500m facile → 3000m+ extrême). Score en temps réel (distance, flips, doubles/triples flips, combo multiplicateur, atterrissages parfaits), écran Game Over avec détection de nouveau record, record persistant.
- **Garage** : 10 voitures aux caractéristiques physiques réellement différentes (vitesse, accélération, poids, stabilité, rotation, adhérence, contrôle aérien), chacune avec sa propre condition de déblocage (niveaux terminés, étoiles, victoires, flips, distance, sans-faute...).
- **Progression** : XP/niveau, page Challenges avec 7 défis réels branchés sur les statistiques du joueur, débloquant XP et voitures.
- **Private multiplayer** : vrai serveur WebSocket. Créer une partie → code à 4 chiffres → lobby temps réel (statuts prêt/hôte) → 3 ou 5 manches sur des circuits générés procéduralement (seed partagée) → chronométrage **autoritaire côté serveur** (le temps est mesuré par le serveur à la réception du message d'arrivée, pas déclaré par le client, donc impossible à tricher en modifiant le JS du navigateur) → classement par manche puis classement général. Testé avec deux navigateurs simultanés.
- **Public multiplayer** : file d'attente réelle, complétée automatiquement par des bots (Easy/Normal/Hard/Expert, résultats non déterministes — jamais deux fois la même course) jusqu'à une taille de lobby cible, système d'élimination par heats (qualification adaptative selon le nombre de participants), écrans QUALIFIÉ!/ÉLIMINÉ, finale et classement.
- **Game feel** : particules (poussière, étincelles, atterrissage), écrans qui tremblent à l'impact, sons synthétisés en temps réel (moteur, flip, crash, atterrissage parfait, victoire — aucun fichier audio externe, donc aucun souci de droits), 6 environnements avec palette et ambiance propres (Neon City, Desert, Industrial, Sky, Volcano, Arctic).
- **Multiplateforme** : contrôle unique (maintenir), au clic/tactile ou à la touche Espace/↑, interface responsive PC/mobile/tablette.

## Ce qui est volontairement simplifié pour cette première version

Conformément à la consigne « construire une base solide puis l'améliorer » :

- Les **bots** du mode Public ne font pas tourner un moteur physique complet côté serveur (ça coûterait cher à grande échelle) : leur temps de course est calculé par un modèle statistique par palier de difficulté (aléatoire à chaque course), et leur position affichée aux autres joueurs est interpolée à partir de ce temps. Ils respectent donc les mêmes règles de résultat que les joueurs réels, mais ne sont pas simulés image par image.
- La taille cible du lobby Public est de 10 (au lieu de 50) par défaut — c'est une constante (`PUBLIC_TARGET_LOBBY_SIZE` dans `shared/constants.ts`) à augmenter quand tu auras plus de joueurs simultanés ; l'architecture (file d'attente + remplissage par bots + heats adaptatifs) supporte déjà 50 sans changement de code.
- La sauvegarde de progression (étoiles, voitures, XP, records) est en `localStorage` (par appareil/navigateur). L'architecture est prête pour brancher une vraie base de données plus tard (voir « Étapes suivantes »).
- Les 20 niveaux Solo et les seuils d'étoiles (bronze/argent/or) sont un premier jet équilibré par estimation ; à ajuster après quelques parties réelles dans `client/src/core/track/levels.ts`.
- 6 environnements ont une palette/ambiance propre ; les décors d'arrière-plan restent simples (formes géométriques en parallaxe) plutôt que des illustrations détaillées.

Rien de tout ça n'est un bouton qui ne fait rien : tout est branché et jouable, juste perfectible.

## Architecture

Monorepo npm workspaces :

```
shared/    types + constantes + RNG déterministe partagés client/serveur
client/    jeu (Vite + TypeScript + Matter.js + Canvas 2D, DOM pour l'UI)
server/    serveur temps réel (Node + ws), salons privés + matchmaking public
```

Le jeu de course tourne entièrement dans le navigateur (canvas + physique locale). Le serveur ne sert que pour le multijoueur : il orchestre les salons/heats, diffuse les positions adverses (« fantômes ») et fait autorité sur les temps de course — aucune logique de jeu sensible ne dépend du client.

## Lancer le projet en local

Prérequis : Node.js 20+.

```bash
# à la racine du repo
npm install

# terminal 1 — serveur multijoueur (WebSocket, port 8787)
npm run dev:server

# terminal 2 — client (Vite, port 5173)
npm run dev:client
```

Ouvre `http://localhost:5173`. Le client se connecte automatiquement à `ws://localhost:8787` pour Private/Public (Solo et Classic n'ont pas besoin du serveur). Pour tester le multijoueur, ouvre l'URL dans deux onglets/navigateurs différents.

## Déployer une vraie URL publique

Il faut déployer **deux services séparés** : le client (fichiers statiques) et le serveur (process Node qui doit rester allumé pour les WebSockets — donc pas d'hébergement purement statique/serverless pour lui).

### 1. Déployer le serveur (WebSocket)

Options gratuites qui supportent un process Node persistant : **Render**, **Railway**, **Fly.io**.

Avec Render (un fichier `render.yaml` est déjà fourni à la racine) :
1. Pousse ce repo sur GitHub.
2. Sur [render.com](https://render.com) → New → Blueprint → sélectionne le repo (Render détecte `render.yaml`).
3. Ou manuellement : New → Web Service → Root Directory `server` → Build Command `npm install` → Start Command `npm run start`.
4. Récupère l'URL générée, par ex. `https://fliprush-server.onrender.com`.

### 2. Déployer le client (statique)

Avec **Vercel** (ou Netlify/Cloudflare Pages, même principe) :
1. New Project → sélectionne le repo → Root Directory `client`.
2. Build Command `npm run build`, Output Directory `dist` (Vercel les détecte automatiquement pour un projet Vite).
3. Ajoute la variable d'environnement `VITE_SERVER_URL` = `wss://fliprush-server.onrender.com` (remplace `wss` par le domaine réel de ton serveur, toujours en `wss://` en production car la page du client est en HTTPS).
4. Déploie → tu obtiens une URL du type `https://fliprush.vercel.app`, partageable immédiatement.

### 3. Domaine personnalisé (optionnel)

Ajoute un domaine (ex. `moncircuit.fr`) dans les réglages du projet Vercel/Netlify, en suivant les instructions DNS qu'ils fournissent (un enregistrement CNAME ou A vers leurs serveurs).

### 4. Base de données (plus tard)

Aucune base de données n'est requise pour l'état actuel (progression solo en `localStorage`, parties multijoueur en mémoire côté serveur). Quand tu voudras des comptes/leaderboards persistants entre appareils, le point d'entrée naturel est `server/src/index.ts` : remplace les `Map` en mémoire par des appels à une base (Postgres via [Neon](https://neon.tech) ou [Supabase](https://supabase.com) ont des tiers gratuits compatibles avec Render/Railway).

## Prochaines étapes suggérées

- Jouer les 20 niveaux Solo pour rééquilibrer les seuils d'étoiles.
- Monter `PUBLIC_TARGET_LOBBY_SIZE` progressivement à mesure que plus de monde joue en simultané.
- Brancher un compte joueur + base de données pour synchroniser la progression entre appareils et ajouter un vrai leaderboard Classic global.
- Enrichir les décors d'arrière-plan par environnement (actuellement des formes simples en parallaxe).
