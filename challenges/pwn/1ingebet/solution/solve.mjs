// solve.mjs — intended solver for 1ingeBet.
// Usage: node solve.mjs [baseUrl]   (default http://127.0.0.1:8080)
//
// Rebuilds every round purely from the public constants shipped in the site's
// source (LCG in rng.js, SEED_STEP in engine.js, deck order + Fisher-Yates in
// deck.js, and the 2-card burn in engine.js), sits out unwinnable rounds, wins
// 10 in a row, and prints the flag. Paces requests under the server's
// ~3 actions/sec rate limit.
const BASE = process.argv[2] || 'http://127.0.0.1:8080';

const SUITS = ['♠', '♥', '♦', '♣'];
const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];
const SEED_STEP = 1337;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const post = async (p, body) => {
  for (;;) {
    const r = await fetch(BASE + p, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {}),
    });
    const json = await r.json();
    if (r.status === 429) { await sleep(400); continue; }
    await sleep(350);
    return { status: r.status, json };
  }
};

const value = (c) => { const r = c.slice(1); return r === 'A' ? 11 : 'JQK'.includes(r) ? 10 : parseInt(r, 10); };
const total = (cards) => {
  let t = 0, a = 0;
  for (const c of cards) { const v = value(c); if (v === 11) a++; t += v; }
  while (t > 21 && a > 0) { t -= 10; a--; }
  return t;
};

function shuffledDeck(seedN) {
  let state = seedN & 0xffff;
  const next = () => { state = (state * 1103515245 + 12345) & 0xffff; return state; };
  const randInt = (n) => Math.floor((next() / 65536) * n);
  const deck = [];
  for (const s of SUITS) for (const r of RANKS) deck.push(s + r);
  for (let i = 51; i >= 1; i--) { const j = randInt(i + 1); [deck[i], deck[j]] = [deck[j], deck[i]]; }
  return deck;
}
// outcome if the player stands on their first 2 cards (deck still has the 2 burn cards at [0..1])
function simulate(deck) {
  const p = [deck[2], deck[4]];
  const d = [deck[3], deck[5]];
  let pos = 6;
  while (total(d) < 17) d.push(deck[pos++]);
  const pt = total(p), dt = total(d);
  return dt > 21 ? 'win' : pt > dt ? 'win' : pt < dt ? 'loss' : 'push';
}

const sess = await post('/api/session');
const seed = sess.json.seed;
const sid = sess.json.sessionId;
console.log(`session started, fair play seed shown once: ${seed}`);

let round = 1;
for (;;) {
  const deck = shuffledDeck((seed + (round - 1) * SEED_STEP) & 0xffff);
  const hole = deck[5];
  const outcome = simulate(deck);
  if (outcome === 'win') {
    await post('/api/action', { sessionId: sid, action: 'deal' });
    const st = await post('/api/action', { sessionId: sid, action: 'stand' });
    console.log(`round ${round}: played  (predicted hole ${hole}, actual ${st.json.dealerHole}) -> ${st.json.result}, streak ${st.json.streak}`);
    if (st.json.flag) { console.log(`\nFLAG: ${st.json.flag}`); process.exit(0); }
  } else {
    const st = await post('/api/action', { sessionId: sid, action: 'sitout' });
    console.log(`round ${round}: sat out (predicted hole ${hole}, outcome would be ${outcome}), streak ${st.json.streak}`);
  }
  round++;
}
