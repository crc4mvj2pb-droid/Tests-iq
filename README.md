# Party Arena

Un site multijoueur à partager par lien : course/parkour 2D à flips ou arène de tir 2D, jusqu'à 10 joueurs, avec des bots pour compléter quand vous n'êtes pas assez nombreux.

## Comment ça marche

Le site est **100% statique** (aucun serveur à héberger ou payer) : le multijoueur passe par une connexion directe entre navigateurs (WebRTC, via le service de signalisation public et gratuit de PeerJS). Celui qui crée la partie devient l'**hôte** : son navigateur fait tourner la simulation du jeu (y compris les bots) et diffuse l'état de la partie aux autres joueurs connectés.

- **Créer une partie** → génère un code + un lien à partager (`?room=CODE`).
- **Rejoindre** → coller le lien ou entrer le code.
- **Jouer seul contre des bots** → aucune connexion réseau nécessaire, tout tourne dans le navigateur.
- Dans le lobby, l'hôte choisit le mode (Course ou Tir), le circuit/la carte, et peut ajouter/retirer des bots.

## Modes de jeu

- **Course** (`src/game/course`) : physique de véhicule (Matter.js) avec alignement au sol et flips en l'air (façon *Rider*) — maintenir pour accélérer, gauche/droite pour flipper pendant les sauts. 3 circuits aux thèmes et difficultés différents (`circuits.ts`).
- **Tir** (`src/game/shooter`) : arène vue du dessus, déplacement + visée (souris sur PC, joystick tactile + tir auto-visée sur mobile), 3 cartes avec des obstacles pour se protéger (`maps.ts`).

Chaque joueur humain choisit un **pseudo et une couleur** avant de jouer (écran de profil, sauvegardé localement).

## Architecture

```
src/
  net/          protocole de messages + connexion PeerJS (hôte/client)
  game/
    course/     circuits, physique (flips), bots, rendu
    shooter/    cartes, simulation, bots, rendu
    GameController.ts   boucle de jeu (simulation hôte à 60Hz, rendu, réseau)
  input/        clavier / souris / contrôles tactiles
  ui/App.ts     écrans (profil, accueil, lobby, HUD, résultats) et logique de partie
```

L'hôte simule à 60 images/s (accélération, rotation en vol, tirs, collisions) et diffuse un instantané complet à chaque frame ; les autres joueurs envoient uniquement leurs entrées (touches pressées) et affichent l'état reçu. Pas d'interpolation réseau complexe : suffisant pour jouer entre proches.

## Lancer le projet en local

```bash
npm install
npm run dev
```

Ouvre `http://localhost:5173`. Pour tester le multijoueur, ouvre l'URL dans deux onglets/navigateurs (le mode solo contre bots ne nécessite qu'un seul onglet).

## Déployer

Le site est statique : n'importe quel hébergeur de fichiers statiques convient (Netlify, Vercel, Cloudflare Pages...). Avec Netlify, `netlify.toml` est déjà configuré (`npm install && npm run build`, dossier `dist`) — il suffit de connecter le dépôt Git dans l'interface Netlify (New site from Git) pour obtenir une URL publique et des déploiements automatiques à chaque push.

## Limites connues

- Le tirage/l'appariement est en pair-à-pair : si l'hôte quitte, la partie s'arrête (pas de migration d'hôte).
- Le WebRTC nécessite une connexion réseau standard côté joueurs (fonctionne dans l'immense majorité des réseaux domestiques/mobiles).
- 3 circuits et 3 cartes pour l'instant ; `circuits.ts` et `maps.ts` sont conçus pour en ajouter facilement d'autres.
