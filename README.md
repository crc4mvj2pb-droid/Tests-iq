# TALUS

Jeu 3D d'escalade et de survie coopérative, jouable au clavier/souris ou au tactile — inspiré par l'idée de *PEAK* (grimper une montagne procédurale en gérant son endurance et sa survie, seul ou avec des amis) mais avec son propre univers, son propre nom, ses propres mécaniques de jeu et un rendu entièrement procédural. Aucun asset, niveau, logo, texture ou ligne de code de *PEAK* n'a été copié.

Le jeu tourne entièrement dans le navigateur (Three.js + WebGL) et s'adapte au téléphone, à la tablette et à l'ordinateur : contrôles clavier/souris avec pointer-lock sur desktop, joystick virtuel + boutons tactiles sur mobile/tablette.

## Ce qui est réellement fonctionnel aujourd'hui

- **Montagne procédurale déterministe** : relief généré par bruit de Simplex superposé à un profil conique, avec un sentier en spirale creusé dans le relief qui offre toujours une route praticable jusqu'au sommet — grimper en ligne droite dans la pente est plus rapide mais plus exigeant. Contreforts doux près de la base, parois plus accidentées près du sommet. Génération identique des deux côtés (client) à partir d'une seed partagée, essentielle pour la coop.
- **Contrôleur de personnage réel** : marche, sprint, saut, et **escalade** (maintenir clic/F ou le bouton tactile dédié sur une paroi assez raide) avec un vrai système de préhension le long de la normale du terrain. Chute libre avec dégâts de chute proportionnels à la hauteur au-delà d'une distance de sécurité.
- **Survie à quatre jauges** : santé, endurance (se vide en escaladant/sprintant, se régénère au sol), faim (diminue en continu, draine la santé à zéro, se restaure avec des baies), froid en altitude (au-delà d'un seuil, sans manteau, draine la santé). Un état « à terre » se déclenche à santé nulle, avec respawn au dernier point de passage après un délai.
- **Objets ramassables** placés proceduralement sur des replats : baies (faim), craie (réduit temporairement la dépense d'endurance à l'escalade), manteau chaud (annule le froid), corde d'ancrage (pose un point de respawn personnalisé). 7 checkpoints en drapeau jalonnent chaque ascension.
- **Coop en ligne réel** : vrai serveur WebSocket. Créer un salon → code à 4 chiffres → lobby (statuts prêt/hôte, jusqu'à 4 joueurs) → décompte de départ → ascension synchronisée sur la même montagne (seed partagée) → positions/animations/vie des coéquipiers diffusées en temps réel → un joueur à terre peut être relevé par un coéquipier à proximité (touche E / bouton tactile dédié) → le sommet atteint par chacun est annoncé aux autres. Testé avec deux navigateurs simultanés (création, jonction, ready, départ, déplacement synchronisé).
- **Caméra troisième personne** avec anti-clipping (raycast contre le terrain, lissage de la distance) et météo dynamique (pluie qui rend les prises plus glissantes, alternée avec des périodes sèches).
- **Multiplateforme** : détection tactile automatique (joystick virtuel + boutons à l'écran) sur mobile/tablette, souris + clavier (ZQSD/flèches, Espace, Shift, F, E, B, R) avec pointer-lock sur desktop. Interface HUD responsive (barres de survie, inventaire, altimètre, minuteur, liste des coéquipiers).

## Ce qui est volontairement simplifié

- Le relief est un champ de hauteur : pas de vrais surplombs/grottes (l'escalade se joue sur des parois raides, pas sous des à-pics négatifs).
- Les avatars sont des silhouettes géométriques simples (capsule + tête), sans animation squelettique — juste un balancement procédural selon l'état (marche/course/escalade/chute/à terre).
- La synchronisation coop diffuse la position/l'état de chaque joueur mais ne fait pas autorité serveur sur la physique (chaque client simule localement) — suffisant pour une coop non compétitive, pas anti-triche.
- Pas de compte joueur ni de classement : rien n'est persisté au-delà du nom/couleur du profil (`localStorage`).

Rien de tout ça n'est un bouton qui ne fait rien : tout est branché et jouable, juste perfectible.

## Architecture

Monorepo npm workspaces :

```
shared/    constantes de simulation, protocole réseau, RNG déterministe partagés client/serveur
client/    jeu (Vite + TypeScript + Three.js + simplex-noise), Canvas WebGL + DOM pour l'UI/HUD
server/    serveur temps réel (Node + ws) pour les salons coop uniquement
```

Le jeu tourne entièrement dans le navigateur (rendu 3D + physique de déplacement locale). Le serveur ne sert que pour la coop : il orchestre le salon/le lobby, diffuse les états des joueurs (position, animation, vie) et relaie les événements (à terre / relevé / sommet atteint) — aucune logique de jeu sensible ne dépend du client, mais la coop n'est pas conçue pour résister à la triche (pas de compétition classée).

## Lancer le projet en local

Prérequis : Node.js 20+.

```bash
# à la racine du repo
npm install

# terminal 1 — serveur coop (WebSocket, port 8787)
npm run dev:server

# terminal 2 — client (Vite, port 5173)
npm run dev:client
```

Ouvre `http://localhost:5173`. Le mode solo n'a pas besoin du serveur. Pour tester la coop, ouvre l'URL dans deux onglets/navigateurs différents (ou sur deux appareils du même réseau via l'URL réseau affichée par Vite).

## Déployer une vraie URL publique

Il faut déployer **deux services séparés** : le client (fichiers statiques) et le serveur (process Node qui doit rester allumé pour les WebSockets — donc pas d'hébergement purement statique/serverless pour lui).

### 1. Déployer le serveur (WebSocket)

Options gratuites qui supportent un process Node persistant : **Render**, **Railway**, **Fly.io**.

Avec Render (un fichier `render.yaml` est déjà fourni à la racine) :
1. Pousse ce repo sur GitHub.
2. Sur [render.com](https://render.com) → New → Blueprint → sélectionne le repo (Render détecte `render.yaml`), ou via le bouton direct : `https://render.com/deploy?repo=<url du repo>`.
3. Ou manuellement : New → Web Service → Root Directory `server` → Build Command `npm install` → Start Command `npm run start`.
4. Récupère l'URL générée, par ex. `https://talus-server.onrender.com`.

### 2. Déployer le client (statique)

Avec **Netlify** (ou Vercel/Cloudflare Pages, même principe) :
1. New site from Git → sélectionne le repo (Netlify détecte `netlify.toml` : base `client`, build `npm install && npm run build`, publish `dist`).
2. Ajoute la variable d'environnement `VITE_SERVER_URL` = `wss://talus-server.onrender.com` (remplace par le domaine réel du serveur, toujours en `wss://` en production).
3. Déploie → tu obtiens une URL partageable immédiatement, utilisable sur téléphone, tablette et ordinateur.

### 3. Domaine personnalisé (optionnel)

Ajoute un domaine dans les réglages du projet Netlify/Vercel, en suivant les instructions DNS qu'ils fournissent.

## Prochaines étapes suggérées

- Ajouter un système de compte/progression persistant entre appareils (remplacer les `Map` en mémoire du serveur par une base type Postgres via Neon/Supabase).
- Varier davantage les biomes (neige, forêt, éboulis) avec des palettes et effets dédiés au-delà de la coloration par altitude/pente actuelle.
- Ajouter de vrais surplombs/grottes (nécessiterait de passer d'un champ de hauteur à une géométrie voxel ou à des meshes de paroi dédiés) pour un gameplay d'escalade plus proche de la référence.
- Étoffer l'animation des personnages (squelette + poses de grimpe) au-delà du balancement procédural actuel.
