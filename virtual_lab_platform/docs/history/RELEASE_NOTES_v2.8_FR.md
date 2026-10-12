# Virtual Lab Platform v2.8 — Cinétique des réseaux réactionnels

## Nouveauté principale

Ajout d’un solveur de cinétique chimique générique, accessible localement via `POST /api/chemistry/kinetics`. Il intègre un réseau de réactions défini par l’utilisateur à l’aide de RK4 à pas fixe. Les vitesses suivent une loi d’action de masse élémentaire à partir des coefficients stœchiométriques des réactifs.

## Exemple de requête

```json
{
  "species": [
    {"id": "A", "initial_concentration": 1.0, "atoms": {"X": 1}},
    {"id": "B", "initial_concentration": 0.0, "atoms": {"X": 1}}
  ],
  "reactions": [
    {"id": "r1", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.4}
  ],
  "duration": 5.0, "dt": 0.01, "temperature_k": 298.15
}
```

Les concentrations et les constantes cinétiques doivent utiliser des unités cohérentes choisies par l’utilisateur. Si `activation_energy_j_mol` et `reference_temperature_k` sont fournis, la constante est ajustée par la relation d’Arrhenius à température constante. Les formules atomiques facultatives permettent de vérifier l’équilibrage de chaque réaction.

## Garde-fous et limites

- Maximum 20 espèces, 20 réactions et 20 000 pas d’intégration.
- Le solveur refuse les réseaux qui produisent des concentrations nettement négatives, afin d’éviter de présenter une intégration instable comme un résultat valide.
- Modèle de milieu parfaitement mélangé, volume constant, sans équilibre, transport, changement de phase ni rétroaction thermique.
- Les paramètres sont fournis par l’utilisateur; ils ne sont pas automatiquement validés par la littérature.
- Ce module n’est pas un solveur universel de chimie et ne prédit pas automatiquement les réactions possibles.

## Tests

La suite de tests complète contient 117 tests réussis, incluant la solution analytique d’une réaction du premier ordre, la dépendance à la température, la détection d’espèces inconnues, l’équilibrage atomique et le rejet d’un pas instable.
