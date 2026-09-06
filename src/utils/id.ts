// Room codes avoid visually ambiguous characters (0/O, 1/I/L).
const CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const ROOM_PREFIX = "partyarena-";

export function generateRoomCode(length = 5): string {
  let out = "";
  for (let i = 0; i < length; i++) {
    out += CODE_CHARS[Math.floor(Math.random() * CODE_CHARS.length)];
  }
  return out;
}

export function roomCodeToPeerId(code: string): string {
  return ROOM_PREFIX + code.trim().toUpperCase();
}

export function generatePlayerUid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function randomColor(index: number): string {
  const palette = [
    "#ff5d73",
    "#4dd6ff",
    "#ffd166",
    "#8b5cf6",
    "#4ade80",
    "#fb923c",
    "#f472b6",
    "#38bdf8",
    "#a3e635",
    "#f87171",
    "#c084fc",
    "#2dd4bf",
  ];
  return palette[index % palette.length];
}
