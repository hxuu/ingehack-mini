let state = 0;

export function srand(seed) {
  state = seed & 0xffff;
}

export function next() {
  state = (state * 1103515245 + 12345) & 0xffff;
  return state;
}

export function randInt(n) {
  return Math.floor((next() / 65536) * n);
}
