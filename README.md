# Oukitel (Wonderfree) — Home Assistant integration

Control and monitor **Oukitel portable power stations** in Home Assistant —
the ones paired through the **Wonderfree** app (`com.quectel.commonappeu`),
sold under names like **Bemo**. Built and tested on an **Oukitel P2001E Plus**,
but nothing here is model-specific.

The station has **no local API of any kind** (see [Why cloud-only](#why-cloud-only)),
so this talks to the same Quectel cloud the app uses. The whole protocol was
reconstructed from the app and verified against the live endpoint.

[![hacs][hacs-badge]][hacs] [![license][license-badge]](LICENSE)

<p align="center">
  <img src="docs/images/station-card.png" width="380" alt="Station dashboard card"/>
  &nbsp;&nbsp;
  <img src="docs/images/light-card.png" width="330" alt="RGB light card"/>
</p>

---

## Features

- **Live telemetry** — battery %, total in/out power, AC charging input, DC
  input, device temperature, remaining charge / discharge time. Every poll asks
  the station to report, so values stay fresh without the app open.
- **Output control** — AC, USB and 12 V DC outputs as switches (verified to
  physically toggle the station).
- **Config flow** — sign in with your Wonderfree account, pick the station.
- **Works while the station sleeps** — reads the cloud's stored last value, so
  entities don't flap to *unavailable*.
- **Bonus dashboard cards** — two polished custom Lovelace cards (below).

### Entities

| Platform | Entities |
|---|---|
| `sensor` | Battery Level · Total In / Out Power · AC In Power · DC In Power · Device Temperature · Charge / Discharge Remaining Time · AC Charging Limit · Last Report (diagnostic) |
| `switch` | AC Output · USB Output · DC (12 V) Output |

Entities are named `sensor.<station>_*` / `switch.<station>_*` (e.g.
`sensor.bemo_battery_level`).

---

## Setup guide

### 1. Install the integration

**HACS (recommended)**

1. HACS → ⋮ (top-right) → **Custom repositories** → add
   `https://github.com/Sporium/ha-oukitel-wonderfree`, category **Integration** → **Add**.
2. Open the new **Oukitel (Wonderfree)** card → **Download** → restart Home Assistant.

**Manual**

Copy the `custom_components/oukitel_wonderfree/` folder into your HA
`config/custom_components/` directory and restart Home Assistant.

### 2. Make a second Wonderfree account and share the station to it

You need **a separate Wonderfree account just for Home Assistant**, signed in
with **email + password**. Don't reuse the account you use on your phone:

- **The cloud allows one session per account.** Signing in to the same account
  in the app logs Home Assistant out, and the other way round. (The integration
  re-logs in by itself, but then your phone gets kicked out.)
- **Google / Apple sign-in has no password**, so Home Assistant can't use it.
- A shared account keeps your main login out of Home Assistant, and you can
  revoke it from the app any time.

Steps (the station stays bound to your main account; the second one gets a share):

1. **Register the second account.** On any phone: Wonderfree app → sign out →
   **sign up with an email** and set a password. Sign out again.
2. **Create the share.** Sign in with your **main** account → open the station →
   **Share to Others** → a **QR code** appears. It is valid for
   30 minutes and works once.
3. **Accept it.** Sign out → sign in with the **second** account → scan the QR
   with the app (easiest from a second phone) → accept.
   The station now shows up in the second account.
4. **Sign out of the second account in the app** and leave it to Home Assistant.
   Keep using your main account on the phone as before.

> If you ever **re-pair the station** (reset, new Wi-Fi) the share is dropped —
> repeat steps 2–3. Home Assistant finds the station again on its own; reload
> the integration afterwards.

### 3. Add the integration in Home Assistant

1. **Settings → Devices & services → + Add integration** → search
   **“Oukitel (Wonderfree)”**.
2. **Username** — the second account's **email**. **Password** — its password.
   → **Submit**.
   - *Invalid authentication*: wrong email/password, or you used a Google/Apple
     account.
   - *No stations found on this account*: the share from step 2–3 wasn't
     accepted yet.
3. **Station** — pick your station from the list → **Submit**.
4. A device appears with all sensors and the AC / USB / DC switches. Entity ids
   follow the station's name in the app, e.g. `sensor.bemo_battery_level`.

**Polling interval:** **Settings → Devices & services → Oukitel (Wonderfree) →
⚙ Configure** (default 30 s, 10–600 s). Each poll also asks the station to
report, so shorter intervals mean fresher data.

> The region defaults to **EU** (`iot-api.quecteleu.com`). For US/China accounts,
> `us` and `cn` are defined in `protocol.REGIONS` (`custom_components/oukitel_wonderfree/protocol.py`).

### 4. (optional) Add the dashboard cards

See [Dashboard cards](#dashboard-cards) below.

---

## Dashboard cards

Two self-contained custom Lovelace cards live in [`www/`](www) — no build step,
no dependencies. They're optional; the integration works without them.

**Install:** copy the `.js` files into `config/www/`, then
**Settings → Dashboards → ⋮ → Resources → Add** each as a **JavaScript Module**
(`/local/oukitel-station-card.js`, `/local/glow-light-card.js`). Add the cards
in the dashboard editor.

### `oukitel-station-card` — station panel

A station-shaped panel: a battery ring, live in/out power, remaining runtime
(or time to full while charging), when the station last reported, and three
tactile toggles for the AC / USB / DC outputs. The status dot turns amber with
"No fresh data" when the last report is older than `stale_min` minutes.

```yaml
type: custom:oukitel-station-card
# all entity ids optional — default to sensor.bemo_* / switch.bemo_*
name: Bemo
model: P2001E Plus
soc: sensor.bemo_battery_level
out: sensor.bemo_total_out_power
in: sensor.bemo_total_in_power
last_report: sensor.bemo_last_report
stale_min: 5
# runtime / time to full: point these at the helpers below — the station's own
# remaining-time values are not usable on the P2001E Plus
discharge_min: sensor.bemo_runtime_left
charge_min: sensor.bemo_time_to_full
# ac_in: sensor.bemo_ac_in_power   # opt-in "Grid in" line; ~0 on P2001E Plus
ac: switch.bemo_ac_output
usb: switch.bemo_usb_output
dc: switch.bemo_dc_output
```

### Runtime estimates (recommended helpers)

On the P2001E Plus the station's *Charge / Discharge Remaining Time* repeat the
same meaningless values, and *AC In Power* stays near 0 even while charging —
charging shows up in *Total In Power*. Note that total input also carries the
pass-through to the outputs (at 100 % input ≈ output), so only `in − out`
reaches the battery. These template sensors are what the card above is fed
with; set `wh_per_pct` to your station's usable Wh per 1 % (16 measured on a
P2001E Plus).

```yaml
# configuration.yaml
sensor:
  - platform: statistics          # smoothed load, 2-minute window
    name: Bemo load 2 min
    entity_id: sensor.bemo_total_out_power
    state_characteristic: average_step
    max_age: { minutes: 2 }
    keep_last_sample: true

template:
  - sensor:
      - name: Bemo runtime left
        unit_of_measurement: min
        device_class: duration
        state: >
          {% set wh_per_pct = 16 %}
          {% set soc = states('sensor.bemo_battery_level') | float(0) %}
          {% set now_w = states('sensor.bemo_total_out_power') | float(0) %}
          {% set avg = states('sensor.bemo_load_2_min') | float(0) %}
          {# a real step in load (>25 % and >30 W) is used at once, not averaged in #}
          {% set p = now_w if avg <= 0 or (now_w - avg) | abs > [30, avg * 0.25] | max else avg %}
          {% if states('sensor.bemo_total_in_power') | float(0) > 5 %}unknown
          {% elif p > 5 %}{{ (soc * wh_per_pct / p * 60) | round(0) }}
          {% else %}unknown{% endif %}
      - name: Bemo time to full
        unit_of_measurement: min
        device_class: duration
        state: >
          {% set wh_per_pct = 16 %}
          {% set soc = states('sensor.bemo_battery_level') | float(0) %}
          {# 0.9 ≈ charger losses #}
          {% set p = states('sensor.bemo_total_in_power') | float(0) - states('sensor.bemo_total_out_power') | float(0) %}
          {% if soc >= 100 %}0
          {% elif p > 10 %}{{ ((100 - soc) * wh_per_pct / (p * 0.9) * 60) | round(0) }}
          {% else %}unknown{% endif %}
```

For "minutes until a cut-off" (e.g. an automation that switches AC off at
20 %), use `(soc - 20)` instead of `soc` in the runtime template.

### `glow-light-card` — RGB light control

A generic RGB light card (works with **any** `light` entity): a live-colour
glow bar, a draggable HS colour wheel, brightness, quick presets, and effect
modes.

```yaml
type: custom:glow-light-card
entity: light.your_rgb_light
name: LED strip
# optional: rename the numbered effects
effect_names:
  "0": Static
  "1": Rainbow
```

---

## Why cloud-only

The station has no local interface. This was measured on a live, responsive
unit, not assumed:

| Probe | Result |
|---|---|
| All 65535 TCP ports (host answering `RST` throughout) | **0 open** |
| Tuya `6668`, Modbus `502`, MQTT `1883`, HTTP `80`/`443` | closed |
| UDP discovery (Tuya heartbeat, mDNS, SSDP), 25 s awake | **0 packets** |
| BLE while joined to Wi-Fi | stops advertising |

It is an outbound-only client of the Quectel cloud, and there was no prior
integration or reverse-engineering to build on.

Quirk worth knowing: the module **ignores ARP** in power-save, so it can look
absent even while connected. A static entry makes it reachable for debugging:
`arp -s <ip> <mac>`.

---

## How it works

Reconstructed from the app and verified against the live EU endpoint
(`iot-api.quecteleu.com`):

- **Login** — `POST .../emailPwdLogin`, form-encoded. The password is
  AES-128-CBC encrypted (key `md5(random).upper()[8:24]`, IV `key[8:16]+key[0:8]`)
  and signed `sha256(email + pwd + random + domain_secret)`. Auth is a plain
  `Authorization: <token>` header plus the app's `X-Q-Language` /
  `quec-random-url` / `app-info` headers — without the latter the gateway
  answers *"please enter token"*.
- **Telemetry** — `getPropertyDataList` per property code, newest row first, so
  `list[0].propertyValue` is the current value and `createTime` is when the
  station reported it (→ *Last Report*).
- **Keeping it fresh** — the station only uploads around a command or while the
  app is open. Each poll writes TSL property `high_frequency_reporting = 3`
  (what the app sends) through the control endpoint, so it keeps reporting
  every ~30 s.
- **Control** — `batchControlDevice` with
  `{"data": "[{\"<code>\": <value>}]", "deviceList": [{productKey, deviceKey}], "type": 2}`.
  The top-level `code:200` only means well-formed — the real result is in
  `data.successList` / `data.failureList`.

`tools/dump.py` logs in and dumps your device's property codes (its TSL) so the
field map can be extended for other models; `tools/probe.py` flattens a
captured response into leaf paths.

---

## Adding another model

The sensor/switch mapping in `api.py` (`FIELD_MAP` / `SWITCH_MAP`) is written
for the P2001E Plus. Other stations use the same protocol but may name their
properties differently. To adapt:

```bash
python3 tools/dump.py --email you@example.com --region eu
```

This prints your station's TSL — the list of property **codes** (e.g.
`battery_percentage`, `ac_switch`). Map the ones you need onto the canonical
keys in `FIELD_MAP` / `SWITCH_MAP` and the entities pick them up. PRs with new
models welcome.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| **Login rejected** on setup | Wrong email/password, or the account has no password (Google/Apple login) — make a second email account (step 2). |
| Phone app keeps **logging you out** | Home Assistant and the phone use the same Wonderfree account — one session per account. Give Home Assistant its own account (step 2). |
| **No stations found** | The account you signed in with has no station bound or shared to it. Re-check the share in the app. |
| Entities show **unavailable** briefly | Normal while the station deep-sleeps; the next poll restores them. |
| Values **frozen** for a long time | Check *Last Report*. If it is old, the station is off Wi-Fi or asleep with nothing to wake it; toggling an output in the app wakes it. |
| **AC In Power** stays 0 while charging | Expected on the P2001E Plus — use *Total In Power* for "is charging / grid present". |
| A **switch flips back** after toggling | The station is asleep — the cloud queues the command and applies it on wake. Outputs that are actually powered toggle instantly. |
| Effect modes show as **“FX 1…8”** | The station only reports effect numbers; name them via the card's `effect_names` option. |

Enable debug logging to see the raw cloud exchange:

```yaml
# configuration.yaml
logger:
  logs:
    custom_components.oukitel_wonderfree: debug
```

---

## Disclaimer

Unofficial. Not affiliated with Oukitel or Quectel. Uses an undocumented cloud
API that the vendor may change at any time. Provided as-is under the
[MIT license](LICENSE).

[hacs]: https://github.com/hacs/integration
[hacs-badge]: https://img.shields.io/badge/HACS-Custom-41BDF5.svg
[license-badge]: https://img.shields.io/badge/license-MIT-blue.svg
