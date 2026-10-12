# Virtual Lab Platform v2.6 — échantillons, équipements et interactions

## Nouveautés
- Les éléments peuvent être déposés sur un bécher, tube, incubateur, thermocycleur PCR, réacteur, microscope, spectrophotomètre, pH-mètre ou centrifugeuse pour devenir le contenu de cet équipement.
- Le panneau Propriétés affiche les échantillons contenus et propose une opération explicite pour la machine sélectionnée.
- Incubateur/chambre thermique : applique la consigne thermique à la propriété de température des échantillons, sans inventer une croissance ou une réaction.
- Spectrophotomètre : calcule l’absorbance Beer–Lambert uniquement si l’utilisateur fournit le coefficient d’extinction, la concentration et le trajet optique.
- pH-mètre : lit une valeur fournie; il ne déduit pas le pH d’une formule chimique.
- Microscope : répertorie les objets contenus sans prétendre générer une image expérimentale.
- PCR : vérifie la présence d’un objet ADN/ARN et décrit le protocole; aucun rendement d’amplification n’est inventé.
- Réacteur : peut exécuter les bilans stœchiométriques existants lorsque tous les réactifs sont présents dans le réacteur. Les quantités des réactifs diminuent et les produits sont ajoutés au contenu.
- La bibliothèque contient maintenant 63 identifiants d’objets uniques, dont de nouveaux équipements et paramètres de physique. Le catalogue demeure une base extensible, pas l’ensemble des connaissances humaines.
- Les relations de contenu sont incluses dans la sauvegarde et l’export JSON existants.

## Limites
- Centrifugation quantitative, amplification PCR quantitative, dynamique moléculaire, structure 3D atomistique, modèle général de cellule et séparation de mélanges ne sont pas implémentés ici.
- Les propriétés d’objets indicatifs ne remplacent pas des fiches fabricant ou des sources scientifiques validées.
- Les câbles électriques restent visuels et ne sont pas encore traduits en netlist automatiquement résolue par le solveur général.
- La bibliothèque scientifique exhaustive devra être alimentée progressivement à partir de bases de données externes sourcées et compatibles avec leurs licences.

## Vérifications dans cette version
- 97 tests Python existants réussis.
- Smoke test des modèles scientifiques réussi.
- Syntaxe JavaScript vérifiée avec `node --check`.
- Les tests navigateur automatisés n’ont pas pu être exécutés dans cet environnement; le rendu dans Safari reste à vérifier sur le Mac de l’utilisateur.
