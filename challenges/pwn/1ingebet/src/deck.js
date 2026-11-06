import { randInt } from './rng.js';

export const SUITS = ['♠', '♥', '♦', '♣'];
export const RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K'];

export function buildDeck() {
  const deck = [];
  for (const suit of SUITS) {
    for (const rank of RANKS) {
      deck.push(suit + rank);
    }
  }
  return deck;
}

export function shuffle(deck) {
  for (let i = 51; i >= 1; i--) {
    const j = randInt(i + 1);
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck;
}

export function cardValue(card) {
  const rank = card.slice(1);
  if (rank === 'A') return 11;
  if (rank === 'J' || rank === 'Q' || rank === 'K') return 10;
  return parseInt(rank, 10);
}

export function handTotal(cards) {
  let total = 0;
  let aces = 0;
  for (const card of cards) {
    const v = cardValue(card);
    if (v === 11) aces += 1;
    total += v;
  }
  while (total > 21 && aces > 0) {
    total -= 10;
    aces -= 1;
  }
  return total;
}
