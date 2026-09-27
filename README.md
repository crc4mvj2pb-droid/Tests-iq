# SOMMET

Un jeu d'escalade coopératif jouable dans le navigateur — sur téléphone, tablette (iPad) et ordinateur — **inspiré de la philosophie de *PEAK*** (gestion d'endurance, chutes qui font mal, objets à ramasser, ascension collective) mais avec son propre univers : des animaux explorateurs stylisés (Marmotte, Corbeau, Renard, Chèvre, Ourson, Lynx), sa propre montagne générée proceduralement, et son propre système d'objets. Aucun asset, personnage, logo ou contenu de *PEAK* n'a été copié.

Le but : grimper depuis le camp de base jusqu'au sommet, seul ou avec ta famille connectée via un code de partie à 4 chiffres.

## Ce qui est réellement fonctionnel

- **Montagne procédurale complète** (Three.js) : un profil radial (prairie → falaise → corniche → falaise → névé → sommet) déformé par du bruit de Perlin seedé, avec deux ravins sombres générés aléatoirement. Couleurs par altitude/pente calculées par sommet (pas de texture externe), ombres portées, ciel en dégradé, mer de nuages, flocons de neige près du sommet.
- **Contrôleur de personnage sur mesure** (pas de moteur physique tiers) : marche/course avec gestion d'endurance, saut, **escalade** des pentes raides (maintenir la prise près d'une falaise fait grimper le personnage le long de la normale au terrain, en consommant de l'endurance — plus la pente est raide, plus ça coûte cher), chute et dégâts si l'atterrissage est trop violent, réapparition au dernier point d'ancrage posé.
- **6 personnages animaux** en low-poly, chacun avec sa silhouette propre (oreilles, cornes, queue, couleurs), animation procédurale des membres (marche, course, escalade, saut, chute, tonneau en cas de chute violente).
- **7 objets différents** à ramasser sur la montagne, avec de vrais effets : gourde (endurance), champignon (effet aléatoire — soin ou étourdissement), corde (pose un point d'ancrage/réapparition), torche (éclaire les ravins sombres 60s), grappin (propulsion automatique vers la corniche la plus proche dans ton champ de vision), fusée éclairante (signale ta position à toute l'équipe), sac renforcé (augmente ton endurance max, permanent).
- **Multijoueur réel sans serveur dédié** : tout tourne sur Netlify (Functions + Blobs, aucun processus Node à héberger ailleurs). Crée une partie → code à 4 chiffres → tes proches le rejoignent depuis leur téléphone/tablette/PC → salle d'attente avec statut prêt/hôte → ascension lancée ensemble sur la même montagne (seed partagée) → tu vois les autres joueurs bouger en temps quasi réel (synchronisation ~2x/seconde), leurs objets ramassés sont retirés pour tout le monde, un toast prévient quand quelqu'un atteint le sommet.
- **Contrôles adaptés à chaque appareil** : détection tactile automatique — joystick virtuel + boutons Saut/Prise sur téléphone et tablette, clavier ZQSD/WASD + glisser-déposer souris sur ordinateur. Interface responsive avec zones de sécurité (encoche, barre de gestes iOS).
- **Ambiance sonore synthétisée en temps réel** (Web Audio API, aucun fichier audio à télécharger) : sauts, atterrissages, ramassage d'objets, chutes, fanfare de victoire.

## Ce qui est volontairement simplifié

- La montagne est une carte de hauteur (pas de vrais surplombs/grottes) : les "ravins sombres" simulent l'ambiance d'un passage obscur nécessitant la torche, sans être de vraies cavités.
- La synchronisation multijoueur se fait par sondage HTTP (~2 fois par seconde) plutôt que par WebSocket : suffisant pour une ascension coopérative, mais pas fait pour un jeu d'action nerveux.
- Pas de compte persistant : le nom et le personnage choisi sont mémorisés localement sur l'appareil (`localStorage`), les parties multijoueur ne gardent pas d'historique.
- Le grappin vise automatiquement la meilleure corniche devant toi plutôt qu'un point précis choisi à la souris.

Rien de tout ça n'est un bouton qui ne fait rien : tout est branché et jouable.

## Architecture

```
shared/            types + RNG seedée partagés client/fonctions
client/             jeu (Vite + TypeScript + Three.js), Canvas + DOM pour l'UI
netlify/functions/   fonctions Netlify (TypeScript) + Netlify Blobs pour l'état des salons multijoueur
```

Un seul site Netlify héberge tout : les fichiers statiques du jeu **et** les fonctions serverless qui font office de "serveur" multijoueur (création de salon, va-et-vient des positions, objets ramassés). Aucun service tiers à payer ou à maintenir séparément.

## Lancer le projet en local

Prérequis : Node.js 20+.

```bash
npm install
npm run dev:client
```

Ouvre `http://localhost:5173`. Le mode solo fonctionne directement. Pour tester le multijoueur en local avec les fonctions Netlify, installe la CLI Netlify (`npm i -g netlify-cli`) puis lance `netlify dev` à la racine à la place de `npm run dev:client`.

## Déployer

Le fichier `netlify.toml` est déjà configuré (base = racine du repo, build du client, dossier `netlify/functions` pour les fonctions). Sur [Netlify](https://app.netlify.com) : *Add new site → Import an existing project* → sélectionne ce repo → Netlify détecte automatiquement la configuration → Déployer. Tu obtiens une URL publique unique à partager avec ta famille.
