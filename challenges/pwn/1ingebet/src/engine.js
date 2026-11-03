import { srand } from './rng.js';
import { buildDeck, shuffle, handTotal } from './deck.js';

export const SEED_STEP = 1337;

export function roundSeed(sessionSeed, round) {
  return (sessionSeed + (round - 1) * SEED_STEP) & 0xffff;
}

export function createRound(sessionSeed, round) {
  srand(roundSeed(sessionSeed, round));
  const deck = shuffle(buildDeck());
  deck.splice(0, 2);
  return {
    number: round,
    deck: deck,
    pos: 4,
    playerCards: [deck[0], deck[2]],
    dealerCards: [deck[1], deck[3]],
    phase: 'player',
    result: null,
  };
}

export function playerHit(r) {
  r.playerCards.push(r.deck[r.pos++]);
  if (handTotal(r.playerCards) > 21) {
    r.phase = 'done';
    r.result = 'loss';
  }
}

export function playerStand(r) {
  while (handTotal(r.dealerCards) < 17) {
    r.dealerCards.push(r.deck[r.pos++]);
  }
  const p = handTotal(r.playerCards);
  const d = handTotal(r.dealerCards);
  if (d > 21 || p > d) r.result = 'win';
  else if (p < d) r.result = 'loss';
  else r.result = 'push';
  r.phase = 'done';
}
