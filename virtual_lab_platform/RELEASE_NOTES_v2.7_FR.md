# Virtual Lab Platform v2.7 — le câblage devient un réseau calculable

## Changement majeur

Les connexions de la paillasse ne sont plus uniquement dessinées entre les cartes. Chaque liaison identifie maintenant une borne de départ et une borne d'arrivée (`a`, `pinA`, `b`, `pinB`). Le graphe des bornes est converti en nœuds électriques par un moteur de topologie dédié, puis envoyé à l'analyse nodale CC existante.

## Corrections en même temps

- Correction d’une case vide accidentelle dans le tableau JavaScript du catalogue, qui pouvait faire échouer l’ajout d’objets situés après cette entrée.
- Suppression d’un token `async` isolé qui déclenchait une erreur JavaScript à l’exécution et interrompait une partie de l’initialisation des anciens panneaux.
- Association explicite des équipements du catalogue (incubateur, bain-marie, PCR, réacteur, microscope, pH-mètre, spectromètre, centrifugeuse) à leurs opérations correspondantes; correction de l’identifiant du pH-mètre et des valeurs par défaut de température/cycles.

## Capacités ajoutées

- Bornes visibles et interactives sur les composants électriques du catalogue.
- Création de câbles en cliquant successivement sur deux bornes ou via les sélecteurs du panneau Propriétés.
- Sauvegarde/restauration des connexions bornes-à-bornes et export JSON du circuit.
- Solveur graphique pour une source idéale CC, une masse, des fils idéaux et un réseau de résistances.
- Résultats par branche : résistance, tension, courant et puissance; tensions de nœuds; résistance équivalente; vérifications KCL et bilan de puissance.
- Validation des connexions incomplètes, source court-circuitée, résistance contournée par un fil, source négative non reliée à la masse et composants non pris en charge.
- Tests de réseaux à une résistance, en série et en parallèle, ainsi que des erreurs de topologie.

## Hypothèses et limites

Le modèle suppose une source CC idéale, des résistances ohmiques constantes et des conducteurs idéaux. Il accepte une seule source et une masse de référence. Les condensateurs, inductances, interrupteurs, diodes, transistors et composants actifs ne sont pas résolus par le solveur graphique, même si des modèles RC/RL ou RLC analytiques existent dans des panneaux séparés. Le logiciel n'est pas SPICE.

Le reste du laboratoire est conservé : interactions machine-échantillon, bilans chimiques limités, modèles scientifiques, analyse CSV, import SBML partiel, provenance et exports.

## Contrôles exécutés

Voir `TEST_RESULTS_v2.7.txt` pour les nombres de tests et les contrôles exécutés dans l'environnement de construction. Le rendu Safari sur le Mac de l'utilisateur et toute validation physique indépendante restent distincts de ces tests.
