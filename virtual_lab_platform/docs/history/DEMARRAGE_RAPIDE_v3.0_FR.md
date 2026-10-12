# Démarrage rapide — Virtual Lab Platform v3.0

1. Décompressez l’archive complète dans un dossier local.
2. Lancez `launch_windows.bat` sur Windows ou `./launch_macos_linux.sh` sur macOS/Linux.
3. Ouvrez l’URL locale affichée par le terminal.
4. Dans le panneau « Simulateur de cinétique chimique », gardez l’exemple A → B ou modifiez les paramètres.
5. Cliquez sur « Exécuter la simulation ».
6. Consultez les courbes et le tableau, puis exportez les résultats en JSON si nécessaire.

## Exemple de départ

- [A] initiale = 1 mol/L ; [B] initiale = 0 mol/L
- k = 0,4 s⁻¹ ; durée = 5 s ; dt = 0,01 s
- température = 298,15 K ; énergie d’activation = 0 J/mol

Pour A → B d’ordre 1, la solution analytique est [A](t) = [A]₀ exp(−kt). À t = 5 s, [A] vaut environ 0,1353 mol/L.

**Important :** la constante de vitesse et ses unités doivent correspondre à la loi cinétique choisie. Ce modèle de démonstration n’est pas un prédicteur universel de réaction chimique.
