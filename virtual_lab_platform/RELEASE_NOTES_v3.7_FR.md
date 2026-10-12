# Notes de version — v3.7

- Ajout d’un moteur d’instruments virtuels connecté à `POST /api/instruments/measure`.
- Lectures simulées reproductibles par graine aléatoire.
- Simulation d’un biais instrumental, correction d’offset, correction de gain et résolution d’affichage.
- Budget d’incertitude explicite : composantes instrumentale, d’étalonnage et de résolution, incertitude-type combinée, incertitude élargie `k=2` et intervalle approximatif.
- Comparaison de la lecture avec la valeur théorique fournie par l’utilisateur.
- Vérification des identifiants d’instrument et des unités ; les appareils sans modèle de mesure ne sont pas acceptés.
- Nouvelle interface dédiée, avec détails du budget et des hypothèses.
- Statut explicite `simulated_measurement` et `experimental_data: false` pour ne jamais présenter la sortie comme une expérience réelle.
- Tests ajoutés pour la reproductibilité, les corrections, le budget d’incertitude et les entrées invalides.

## Limites connues
Le modèle est un outil pédagogique. Il ne remplace pas un certificat d’étalonnage, un instrument réel ni une validation métrologique. Les spécifications du catalogue sont illustratives. Dérive, hystérésis, temps de réponse, environnement et traçabilité ne sont pas simulés.
