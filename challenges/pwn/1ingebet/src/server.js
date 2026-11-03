import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createRound, playerHit, playerStand } from './engine.js';
import { handTotal } from './deck.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC_DIR = path.join(__dirname, 'public');
const PORT = Number(process.env.PORT || 8080);
const FLAG_PATH = process.env.FLAG_PATH || path.join(__dirname, 'flag.txt');
const SESSION_TTL_MS = Number(process.env.SESSION_TTL_MS || 2 * 60 * 60 * 1000);
const RATE_WINDOW_MS = Number(process.env.RATE_WINDOW_MS || 1000);
const RATE_MAX = Number(process.env.RATE_MAX || 3);
const MAX_BODY_BYTES = 16 * 1024;

const SHARED_FILES = new Map([
  ['/rng.js', path.join(__dirname, 'rng.js')],
  ['/deck.js', path.join(__dirname, 'deck.js')],
  ['/engine.js', path.join(__dirname, 'engine.js')],
]);

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.svg': 'image/svg+xml',
};

let FLAG = (process.env.FLAG || '').trim();
if (!FLAG) {
  try {
    FLAG = fs.readFileSync(FLAG_PATH, 'utf8').trim();
  } catch {
    console.error(`warning: no FLAG env and could not read flag file at ${FLAG_PATH} (flag will be empty)`);
  }
}

const sessions = new Map();

function getSession(id) {
  const s = sessions.get(id);
  if (!s) return null;
  if (Date.now() - s.createdAt > SESSION_TTL_MS) {
    sessions.delete(id);
    return null;
  }
  return s;
}

function handleSession() {
  const sessionId = crypto.randomBytes(16).toString('hex');
  const seed = 1 + crypto.randomInt(65535);
  sessions.set(sessionId, {
    seed: seed,
    round: 1,
    streak: 0,
    solved: false,
    current: null,
    createdAt: Date.now(),
    actions: [],
  });
  return { status: 200, body: { sessionId: sessionId, seed: seed } };
}

function buildState(s) {
  const r = s.current;
  const done = !!r && r.phase === 'done';
  return {
    round: r ? r.number : s.round,
    phase: r ? r.phase : 'done',
    playerCards: r ? r.playerCards.slice() : [],
    playerTotal: r ? handTotal(r.playerCards) : 0,
    dealerUp: r && r.dealerCards.length > 0 ? r.dealerCards[0] : null,
    dealerHole: done && r.dealerCards.length > 1 ? r.dealerCards[1] : null,
    dealerCards: done && r ? r.dealerCards.slice() : null,
    dealerTotal: done && r ? handTotal(r.dealerCards) : null,
    result: r ? r.result : null,
    streak: s.streak,
    flag: s.solved ? FLAG : null,
  };
}

function finishRound(s) {
  const result = s.current.result;
  if (result === 'win') s.streak += 1;
  else if (result === 'loss') s.streak = 0;
  if (s.streak >= 10) s.solved = true;
  s.round += 1;
}

function handleAction(body) {
  if (typeof body !== 'object' || body === null) {
    return { status: 400, body: { error: 'JSON body required' } };
  }
  const sessionId = body.sessionId;
  const action = body.action;
  if (typeof sessionId !== 'string' || typeof action !== 'string') {
    return { status: 400, body: { error: 'sessionId and action are required' } };
  }
  const s = getSession(sessionId);
  if (!s) return { status: 404, body: { error: 'unknown or expired session' } };

  const now = Date.now();
  s.actions = s.actions.filter((t) => now - t < RATE_WINDOW_MS);
  if (s.actions.length >= RATE_MAX) {
    return { status: 429, body: { error: 'rate limited: slow down' } };
  }
  s.actions.push(now);

  if (!['deal', 'hit', 'stand', 'sitout'].includes(action)) {
    return { status: 400, body: { error: 'unknown action: ' + action } };
  }

  const r = s.current;
  const phase = r ? r.phase : 'done';

  if (action === 'deal') {
    if (phase === 'player') return { status: 400, body: { error: 'round already in progress' } };
    s.current = createRound(s.seed, s.round);
  } else if (action === 'hit') {
    if (phase !== 'player') return { status: 400, body: { error: 'hit is only allowed during the player phase' } };
    playerHit(s.current);
    if (s.current.phase === 'done') finishRound(s);
  } else if (action === 'stand') {
    if (phase !== 'player') return { status: 400, body: { error: 'stand is only allowed during the player phase' } };
    playerStand(s.current);
    finishRound(s);
  } else if (action === 'sitout') {
    if (phase === 'player') {
      s.current.result = 'sitout';
      s.current.phase = 'done';
    } else {
      s.current = { number: s.round, deck: [], pos: 0, playerCards: [], dealerCards: [], phase: 'done', result: 'sitout' };
    }
    s.round += 1;
  }

  return { status: 200, body: buildState(s) };
}

function respond(res, out) {
  const payload = JSON.stringify(out.body);
  res.writeHead(out.status, {
    'Content-Type': 'application/json; charset=utf-8',
    'X-Content-Type-Options': 'nosniff',
  });
  res.end(payload);
}

function readBody(req, res, cb) {
  const chunks = [];
  let size = 0;
  req.on('data', (chunk) => {
    size += chunk.length;
    if (size > MAX_BODY_BYTES) {
      respond(res, { status: 413, body: { error: 'body too large' } });
      req.destroy();
      return;
    }
    chunks.push(chunk);
  });
  req.on('end', () => {
    let body;
    try {
      body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    } catch {
      return respond(res, { status: 400, body: { error: 'invalid JSON body' } });
    }
    cb(body);
  });
  req.on('error', () => respond(res, { status: 400, body: { error: 'bad request' } }));
}

function sendFile(res, filePath, headOnly) {
  fs.stat(filePath, (err, st) => {
    if (err || !st.isFile()) {
      return respond(res, { status: 404, body: { error: 'not found' } });
    }
    const type = MIME[path.extname(filePath).toLowerCase()] || 'application/octet-stream';
    res.writeHead(200, {
      'Content-Type': type,
      'Content-Length': st.size,
      'X-Content-Type-Options': 'nosniff',
    });
    if (headOnly) return res.end();
    fs.createReadStream(filePath).pipe(res);
  });
}

function serveStatic(pathname, req, res) {
  if (SHARED_FILES.has(pathname)) {
    return sendFile(res, SHARED_FILES.get(pathname), req.method === 'HEAD');
  }
  const rel = pathname === '/' ? 'index.html' : pathname.slice(1);
  const filePath = path.normalize(path.join(PUBLIC_DIR, rel));
  if (filePath !== PUBLIC_DIR && !filePath.startsWith(PUBLIC_DIR + path.sep)) {
    return respond(res, { status: 404, body: { error: 'not found' } });
  }
  sendFile(res, filePath, req.method === 'HEAD');
}

const server = http.createServer((req, res) => {
  let pathname;
  try {
    pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  } catch {
    return respond(res, { status: 400, body: { error: 'bad request' } });
  }
  if (req.method === 'POST' && pathname === '/api/session') {
    return readBody(req, res, () => respond(res, handleSession()));
  }
  if (req.method === 'POST' && pathname === '/api/action') {
    return readBody(req, res, (body) => respond(res, handleAction(body)));
  }
  if (req.method === 'GET' || req.method === 'HEAD') {
    return serveStatic(pathname, req, res);
  }
  respond(res, { status: 405, body: { error: 'method not allowed' } });
});

server.listen(PORT, () => {
  console.log(`1ingeBet listening on http://0.0.0.0:${PORT}`);
});
