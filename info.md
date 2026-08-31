# Oukitel (Wonderfree)

Monitor and control **Oukitel portable power stations** (Wonderfree app /
"Bemo") in Home Assistant. Built on a **P2001E Plus**.

The station exposes no local API, so this uses the Quectel cloud — the protocol
was reverse-engineered from the app and verified live.

**Provides:** battery %, in/out power, AC/DC input, temperature, remaining
charge/discharge time, and AC / USB / DC output switches.

After install: **Settings → Devices & Services → Add Integration → Oukitel
(Wonderfree)** and sign in with your Wonderfree account (a shared second
account works too).

Two optional dashboard cards are included in `www/` — a station panel and an
RGB light card.
