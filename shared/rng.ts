/** Deterministic seeded PRNG (mulberry32). Same seed -> same sequence,
 * which is what lets every client in a multiplayer round render an
 * identical procedurally-generated track from just a shared numeric seed. */
export function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function randSeed(): number {
  return (Math.random() * 0xffffffff) >>> 0;
}
