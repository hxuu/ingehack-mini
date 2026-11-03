'use strict';

var sessionId = null;
var fairSeed = null;
var lastFlag = null;

function $(id) { return document.getElementById(id); }

function post(url, body) {
  return fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  }).then(function (res) {
    return res.text().then(function (text) {
      var data = null;
      try { data = JSON.parse(text); } catch (e) { /* non-JSON error body */ }
      if (!res.ok) {
        var err = new Error((data && data.error) || ('HTTP ' + res.status));
        err.status = res.status;
        throw err;
      }
      return data;
    });
  });
}

function setMessage(text) {
  $('message').textContent = text || '';
}

function cardEl(text, hidden) {
  var d = document.createElement('div');
  d.className = 'card' + (hidden ? ' back' : '');
  d.textContent = hidden ? '🂠' : text;
  return d;
}

var RESULT_TEXT = {
  win: 'You win the round!',
  loss: 'Dealer takes the round.',
  push: 'Push — streak unchanged.',
  sitout: 'Sitting out this round.',
};

function render(s) {
  $('round').textContent = 'Round: ' + (s.round || '–');
  $('streak').textContent = 'Streak: ' + s.streak + ' / 10';

  var pc = $('playerCards');
  pc.innerHTML = '';
  s.playerCards.forEach(function (c) { pc.appendChild(cardEl(c, false)); });
  $('playerTotal').textContent = s.playerCards.length ? '= ' + s.playerTotal : '';

  var dc = $('dealerCards');
  dc.innerHTML = '';
  if (s.dealerCards) {
    s.dealerCards.forEach(function (c) { dc.appendChild(cardEl(c, false)); });
  } else if (s.dealerUp) {
    dc.appendChild(cardEl(s.dealerUp, false));
    dc.appendChild(cardEl('', true));
  }
  $('dealerTotal').textContent = (s.dealerTotal != null && s.dealerCards && s.dealerCards.length) ? '= ' + s.dealerTotal : '';

  if (s.result) setMessage(RESULT_TEXT[s.result] || s.result);

  var inPlayer = s.phase === 'player';
  $('btnDeal').disabled = !sessionId || inPlayer;
  $('btnHit').disabled = !sessionId || !inPlayer;
  $('btnStand').disabled = !sessionId || !inPlayer;
  $('btnSitout').disabled = !sessionId;

  if (s.flag) {
    lastFlag = s.flag;
    $('prizeArea').hidden = false;
  }
}

function showPrize() {
  if (lastFlag) {
    $('flagOut').textContent = lastFlag;
    $('flagOut').hidden = false;
  }
}

function act(action) {
  if (!sessionId) return;
  post('/api/action', { sessionId: sessionId, action: action })
    .then(render)
    .catch(function (e) { setMessage(e.message); });
}

function newSession() {
  post('/api/session')
    .then(function (r) {
      sessionId = r.sessionId;
      fairSeed = r.seed;
      $('seedBox').textContent = 'Fair play seed: ' + fairSeed;
      $('seedBox').hidden = false;
      setMessage('Session started. Good luck.');
      render({ round: 0, phase: 'done', playerCards: [], playerTotal: 0, dealerUp: null, dealerHole: null, dealerCards: null, dealerTotal: null, result: null, streak: 0, flag: null });
    })
    .catch(function (e) { setMessage('Could not start session: ' + e.message); });
}

newSession();
