import "./style.css";
import { App } from "./ui/App";

// Belt-and-suspenders against mobile double-tap-to-zoom: some browsers
// (notably iOS Safari) can still trigger it from rapid taps even with
// touch-action: none and a locked viewport meta tag.
let lastTouchEnd = 0;
document.addEventListener(
  "touchend",
  (e) => {
    const now = Date.now();
    if (now - lastTouchEnd <= 350) e.preventDefault();
    lastTouchEnd = now;
  },
  { passive: false }
);
document.addEventListener("gesturestart", (e) => e.preventDefault());

const root = document.getElementById("app")!;
new App(root).start();
