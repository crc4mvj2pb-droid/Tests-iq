# FlipRush

Jeu de course arcade 2D à physique — inspiré de la philosophie de *Rider* (accélération/rotation en vol, flips, atterrissages précis, terrain qui roule en continu) mais avec son propre univers, ses propres voitures et son propre système de progression. Aucun asset, niveau, logo ou contenu de Rider n'a été copié : identité visuelle, noms et environnements sont originaux.

Le jeu est volontairement recentré sur l'essentiel : **une course infinie type Rider**, **des voitures aux physiques réellement différentes**, et **une partie privée pour jouer avec ses amis**.

## Ce qui est réellement fonctionnel aujourd'hui

- **Moteur physique réel** (Matter.js) : voiture à châssis + 2 roues motrices sur suspensions, gravité, inertie, friction, collisions. Tenir le bouton accélère ; en l'air, tenir le bouton fait tourner le nez pour les flips. Au sol, la voiture reste plaquée à la pente du terrain (elle ne bascule pas toute seule) — la rotation libre n'existe qu'en vol, comme dans le jeu de référence.
- **Terrain procédural fluide** : collines qui roulent en continu (deux ondes sinusoïdales superposées, jamais deux fois le même terrain), avec des obstacles distincts insérés de temps en temps (rampes, gaps, loops, tunnels, murs, plateformes mobiles) plutôt qu'un enchaînement ininterrompu d'obstacles. La difficulté augmente progressivement avec la distance. Un tronçon plat garanti est toujours placé juste après le départ, pour ne jamais démarrer devant un trou.
- **Course infinie** (écran « JOUER ») : pas de ligne d'arrivée, score en temps réel (distance, flips, doubles/triples flips, combo multiplicateur, atterrissages parfaits), un crash termine la course, écran Game Over avec détection de nouveau record, record persistant en local.
- **Garage** : 10 voitures aux caractéristiques physiques réellement différentes (vitesse, accélération, poids, stabilité, rotation, adhérence, contrôle aérien) — pas de simples skins — chacune avec sa propre condition de déblocage (distance parcourue, flips, score, combo, victoires Private).
- **Private multiplayer** : vrai serveur WebSocket. Créer une partie → code à 4 chiffres → lobby temps réel (statuts prêt/hôte) → 3 ou 5 manches sur des circuits générés procéduralement (seed partagée, donc identiques pour tous les joueurs d'une manche) → chronométrage **autoritaire côté serveur** (le temps est mesuré par le serveur à la réception du message d'arrivée, pas déclaré par le client — impossible à tricher en modifiant le JS du navigateur) → classement par manche puis classement général. Testé avec deux navigateurs simultanés.
- **Game feel** : particules (poussière, étincelles, atterrissage), écran qui tremble à l'impact, sons synthétisés en temps réel (moteur, flip, crash, atterrissage parfait, victoire — aucun fichier audio externe), 6 environnements avec palette et ambiance propres (Neon City, Desert, Industrial, Sky, Volcano, Arctic).
- **Multiplateforme** : contrôle unique (maintenir), au clic/tactile ou à la touche Espace/↑, interface responsive PC/mobile/tablette.

## Ce qui est volontairement simplifié

- La sauvegarde de progression (voitures débloquées, XP, records) est en `localStorage` (par appareil/navigateur). L'architecture est prête pour brancher une vraie base de données plus tard.
- 6 environnements ont une palette/ambiance propre ; les décors d'arrière-plan restent simples (formes géométriques en parallaxe) plutôt que des illustrations détaillées.

Rien de tout ça n'est un bouton qui ne fait rien : tout est branché et jouable, juste perfectible.

## Architecture

Monorepo npm workspaces :

```
shared/    types + constantes + RNG déterministe partagés client/serveur
client/    jeu (Vite + TypeScript + Matter.js + Canvas 2D, DOM pour l'UI)
server/    serveur temps réel (Node + ws) pour les salons Private uniquement
```

Le jeu tourne entièrement dans le navigateur (canvas + physique locale). Le serveur ne sert que pour Private : il orchestre le salon/les manches, diffuse les positions adverses (« fantômes ») et fait autorité sur les temps de course — aucune logique de jeu sensible ne dépend du client.

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

Ouvre `http://localhost:5173`. Le client se connecte automatiquement à `ws://localhost:8787` pour Private (le mode infini n'a pas besoin du serveur). Pour tester le multijoueur, ouvre l'URL dans deux onglets/navigateurs différents.

## Déployer une vraie URL publique

Il faut déployer **deux services séparés** : le client (fichiers statiques) et le serveur (process Node qui doit rester allumé pour les WebSockets — donc pas d'hébergement purement statique/serverless pour lui).

### 1. Déployer le serveur (WebSocket)

Options gratuites qui supportent un process Node persistant : **Render**, **Railway**, **Fly.io**.

Avec Render (un fichier `render.yaml` est déjà fourni à la racine) :
1. Pousse ce repo sur GitHub.
2. Sur [render.com](https://render.com) → New → Blueprint → sélectionne le repo (Render détecte `render.yaml`), ou via le bouton direct : `https://render.com/deploy?repo=<url du repo>`.
3. Ou manuellement : New → Web Service → Root Directory `server` → Build Command `npm install` → Start Command `npm run start`.
4. Récupère l'URL générée, par ex. `https://fliprush-server.onrender.com`.

### 2. Déployer le client (statique)

Avec **Netlify** (ou Vercel/Cloudflare Pages, même principe) :
1. New site from Git → sélectionne le repo (Netlify détecte `netlify.toml` : base `client`, build `npm install && npm run build`, publish `dist`).
2. Ajoute la variable d'environnement `VITE_SERVER_URL` = `wss://fliprush-server.onrender.com` (remplace par le domaine réel du serveur, toujours en `wss://` en production).
3. Déploie → tu obtiens une URL partageable immédiatement.

### 3. Domaine personnalisé (optionnel)

Ajoute un domaine dans les réglages du projet Netlify/Vercel, en suivant les instructions DNS qu'ils fournissent.

### 4. Base de données (plus tard)

Aucune base de données n'est requise pour l'état actuel (progression en `localStorage`, parties Private en mémoire côté serveur). Pour des comptes/leaderboards persistants entre appareils, le point d'entrée naturel est `server/src/index.ts` : remplacer les `Map` en mémoire par des appels à une base (Postgres via [Neon](https://neon.tech) ou [Supabase](https://supabase.com), tiers gratuits compatibles avec Render/Railway).

## Prochaines étapes suggérées

- Brancher un compte joueur + base de données pour synchroniser la progression entre appareils.
- Enrichir les décors d'arrière-plan par environnement (actuellement des formes simples en parallaxe).
- Ajouter d'autres modes si besoin plus tard (l'ancien code Solo/Public/Challenges a été retiré pour se concentrer sur l'essentiel, mais le catalogue de 59 obstacles dans `client/src/core/track/segments.ts` reste disponible pour en reconstruire).
