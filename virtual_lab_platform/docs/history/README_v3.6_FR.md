# Virtual Lab Platform v3.6

## Démarrer
- macOS/Linux : `python3 app.py`
- Windows : `python app.py`
- Ouvrir ensuite http://127.0.0.1:8765.

## Nouveauté principale : bilan stœchiométrique côté serveur
Le calcul de réaction de la paillasse passe maintenant par le moteur Python `reaction_stoichiometry.py` via `/api/chemistry/stoichiometry`.

Le moteur calcule :
- l'avancement théorique maximal ;
- le ou les réactifs limitants ;
- les quantités restantes de réactifs ;
- les quantités théoriques de produits ;
- un contrôle de conservation des atomes lorsque toutes les formules sont disponibles.

Si les formules sont présentes et que l'équation n'est pas équilibrée, le calcul est refusé et la paillasse n'est pas modifiée. Si une formule manque, le bilan atomique est indiqué comme non vérifié (niveau L0), jamais comme validé.

## Portée scientifique
Ce calcul est un bilan de matière idéal, pas une simulation de cinétique, d'équilibre ou de rendement. Une équation équilibrée ne prouve pas qu'une réaction est réalisable dans des conditions données. Il faut toujours vérifier les hypothèses, les unités et la sécurité avant tout usage réel.
