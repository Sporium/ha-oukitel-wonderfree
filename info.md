# Oukitel (Wonderfree)

Monitor and control **Oukitel portable power stations** (Wonderfree app /
"Bemo") in Home Assistant. Built on a **P2001E Plus**.

The station exposes no local API, so this uses the Quectel cloud — the protocol
was reverse-engineered from the app and verified live.

**Provides:** battery %, in/out power, AC/DC input, temperature, remaining
charge/discharge time, and AC / USB / DC output switches.

**Before setup, make a second Wonderfree account** (email + password) and share
the station to it from your main account (*Share to Others* → QR). The cloud
allows one session per account, so Home Assistant and your phone can't share
one login. Then: **Settings → Devices & Services → Add Integration → Oukitel
(Wonderfree)** and sign in with the second account. Full steps in the README.

Two optional dashboard cards are included in `www/` — a station panel and an
RGB light card.
