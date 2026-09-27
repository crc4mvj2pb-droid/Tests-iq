export interface MenuCallbacks {
  onSolo: () => void;
  onCoop: () => void;
}

export function renderMenu(root: HTMLElement, cb: MenuCallbacks): () => void {
  const el = document.createElement('div');
  el.className = 'screen';
  el.innerHTML = `
    <h1 class="talus-title">TALUS</h1>
    <p class="talus-tagline">Grimpez, survivez, atteignez le sommet — seul ou avec vos amis.
      Gérez votre stamina, votre faim et le froid en altitude sur une montagne procédurale.</p>
    <div class="menu-buttons">
      <button class="btn btn-primary" data-action="solo">Grimper en solo</button>
      <button class="btn btn-secondary" data-action="coop">Partie entre amis (coop)</button>
    </div>
    <p class="talus-disclaimer">
      TALUS est un jeu original inspiré par l'idée d'escalade-survie coopérative,
      avec son propre univers, ses propres mécaniques et aucun contenu copié d'un autre jeu.
      Desktop : ZQSD/flèches + souris, Espace pour sauter, maintenir clic/F pour s'agripper.
      Mobile/tablette : joystick + boutons tactiles à l'écran.
    </p>
  `;
  root.appendChild(el);

  const onClick = (e: Event) => {
    const target = e.target as HTMLElement;
    const action = target.dataset.action;
    if (action === 'solo') cb.onSolo();
    if (action === 'coop') cb.onCoop();
  };
  el.addEventListener('click', onClick);

  return () => {
    el.removeEventListener('click', onClick);
    el.remove();
  };
}
