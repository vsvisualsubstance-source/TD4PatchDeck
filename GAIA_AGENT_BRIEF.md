<!-- Prepared by Claude (TD-Gaia/Agent session), 2026-08-18. Handoff brief for building a Gaia Agent inside PatchDeck. -->

# Gaia Agent for PatchDeck — build brief

## Goal

PatchDeck should receive the Gaia data feeds (house mood, presence, rooms, gamification, dream, etc.)
so its own visual modules can consume them — reusing or rebuilding PatchDeck-native effects, not
copying the TD-Gaia project's network. Scope: **ingest everything now, decide what to use later.**

This brief was prepared from a separate Claude Code session working the TD-Gaia project
(`/Users/maurospagnoli/Documents/TD/Agent`, repo `TD4Gaia`), which cannot reach PatchDeck's live
TD network directly (different `.mcp.json`/Envoy bridge, different project). Use this doc instead of
re-deriving the schema from scratch.

## Transport decision: MQTT, not OSC

TD-Gaia's existing project ingests Gaia via **OSC on UDP port 7000** (`oscin1`). That is a unicast
port — if PatchDeck and TD-Gaia might ever run **at the same time on this Mac**, they cannot both
bind port 7000. Since it wasn't yet decided whether PatchDeck runs standalone or alongside TD-Gaia,
**MQTT is the safer default**: it's pub/sub, so any number of subscribers (including TD-Gaia's own
MQTT bridge, which already runs) can read the same topics with zero port conflict, whether PatchDeck
runs alone or in parallel.

**Broker**: `tcp://192.168.1.142:1883` (LAN, confirmed reachable, no auth observed). This is Gaia's
real broker — not `localhost`, that was a wrong default guess in an earlier build.

## Verified live on 2026-08-18 — subscribe to these 3 topics

Sampled directly off the broker with `mosquitto_sub -h 192.168.1.142 -p 1883 -t '#' -v`. These three
topics alone cover almost the entire Gaia data surface as JSON blobs:

### `gaia/td/canvas`
Mirrors the documented `gaia/canvas/*` OSC schema **plus more that's grown since**: `soul`
(mood/mood_rgb/stress/calm/social/curiosity/energy/lifeIndex), `rooms` (per-room presence_count,
activity, temperature, darkness, emotion/pose/gesture, objects with deterministic `seed`), `lights`
(per-fixture power/brightness/color/colorTemp — real house DMX-relevant state), `bricks`, `lexicon`
(word → count/seed), `dream` (mood + words with seeds), plus newer fields not in the old schema doc:
`thought`, `thoughts[]` (recent LLM "thoughts" with timestamps), `tts`/`ttsTs`/`ttsRoom`,
`lastMemory`/`memories[]`, `diary[]` (structured event log: mediapipe/vision entries), `voiceCommands[]`.

### `gaia/brain/state`
Richer/rawer than the canvas mirror. Notably includes:
- `gamification`: `{level, xp, xpNextLevel, activeClass, unlockedAssets[], stats: {mago, bardo, guerriero, druido}}` — this **is** the progression/RPG-class data (previously only seen on OSC `gaia/progression/*`, now confirmed mirrored here too).
- `presence`: per-person object (`mauro`, `eli`, `maurizio`, `nicola`, ...) with `present`, `enterTs`, `lastSeen`, `room`, `confidence`, `track_id`, `pose`, `exitTs` — richer than the old `gaia/people/*` OSC namespace (affinity/visits fields not present here; may still be OSC-only, unverified).
- `rooms`: a more detailed per-room state than the canvas mirror (raw `_yolo`/`_mediapipe` flags, `main_user`, `zone`, per-room `mediapipe.people[]` breakdown).
- `mood`, `lifeIndex` (duplicates of canvas's `soul` fields, same values).

### `gaia/brain/dream`
Simple: `{ts, text, words[], mood}` — the last nighttime dream as prose + word list. Subset of what
`gaia/td/canvas`'s `dream` field already carries, but arrives standalone/sooner.

**Sample payloads** (captured live, trimmed for size) are in `gaia_agent_sample_payloads.json` next to
this file — read that before writing any JSON-parsing code, to see real field shapes/nesting instead
of guessing types.

## Known gaps — NOT seen on MQTT (2026-08-18 sample)

- **`gaia/mocap/*`** (raw 3D landmark tracking — pose/hands/face, thousands of channels) — not observed
  on the broker in an 8s sample. Almost certainly OSC-only; too high-frequency/high-channel-count for
  a JSON MQTT blob. If PatchDeck needs mocap, it likely needs its own OSC listener on a **different
  port** than 7000 (would require the Gaia/Node-RED sender to be reconfigured to also emit to a second
  destination) — a separate decision, don't build this speculatively.
- **`gaia/plants/*`** (basilico/salvia health/moisture) — not observed either. Could be a publish-rate
  miss (short sampling window) or deprecated. Re-check with a longer sniff (`mosquitto_sub -h
  192.168.1.142 -p 1883 -t 'gaia/plants/#' -v`, wait 60s+) before assuming it's gone.

Also note: this whole brief is a **point-in-time snapshot** (2026-08-18). Gaia's schema has visibly
grown since the last time it was fully documented (~3 weeks prior) — re-verify against live broker
traffic before trusting field names blindly, the same way this brief was produced.

## Build pattern — follow TD-Gaia's proven implementation, don't reinvent

TD-Gaia's `/project1/container1/Bridge/mqtt_bridge` and `Bridge/gaia_agent` already solved this
exact problem (subscribing to Gaia's MQTT, parsing JSON, avoiding the crashes). Mirror that pattern:

1. **Use TD's native `mqttclientDAT`** — not `paho.mqtt.client`. The native DAT dispatches
   `onConnect`/`onMessage` on TD's main thread with zero thread-safety machinery needed, and has no
   `sys.path`/venv dependency (works even if Envoy/Embody's venv isn't available at runtime).
2. **Centralize config** in one `gaia_config`-style COMP/custom pars (`Brokerhost`, `Brokerport`) —
   don't hardcode the IP on multiple ops.
3. **JSON parsing**: `onMessage(dat, topic, payload, qos, retained, dup)` → `payload` arrives as raw
   **`bytes`** at runtime despite TD's own scaffold typing it `str` — always
   `payload.decode('utf-8', errors='replace')` before `json.loads()`, or downstream data silently
   corrupts into a `"b'...'"` string repr with no error.
4. Route each topic's parsed JSON into whatever shape PatchDeck's downstream needs (Script CHOP for
   numeric fan-out, Table DAT for structured/string data) — TD-Gaia's `script_canvas` /
   `script_canvas_strings` pair is a reusable pattern: numeric fields as CHOP channels named to match
   the OSC-equivalent addresses (`gaia/canvas/soul/mood_rgb/r` etc.) for drop-in compatibility with
   any effect built against the OSC schema, strings in a parallel DAT since OSC can't carry them.

### mqttclientDAT gotchas (verified on TD-Gaia, will bite here too)

- `dat.isConnected` is a **property**, not a method — `dat.isConnected()` raises `TypeError`.
- `dat.publish(topic, payload, ...)` needs `payload` as **`bytes`** — `json.dumps(...).encode('utf-8')`,
  a plain `str` raises "Second argument must by bytes object".
- The DAT's own output table is a single unstructured `message` column — all real per-topic routing
  must happen inside the Callbacks DAT's `onMessage`, not by reading the table.
- Custom `Str`/`Int` pars created via `appendStr()`/`appendPulse()` set `.default` but **not the live
  `.val`** — always set both, or the parameter silently reads back as blank/clamped.

### Crash-avoidance (cost 3 TD crashes to learn on TD-Gaia — don't repeat)

- **Don't edit a live-firing callback DAT** (one actively receiving real-time MQTT messages) with
  `edit_dat_content`/`set_dat_content` while traffic is flowing. Build/wire the whole module with the
  MQTT client **inactive/disconnected** first, write the callback code correctly in one pass, `project.save()`
  as a checkpoint, **then** flip `Active=1` and verify.
- **Once connected, avoid toggling `mqttclientDAT.par.active` off/on** — this alone crashed TD once on
  TD-Gaia with no code changes involved. If you need to reconfigure, disconnect fully, make all edits,
  save, reconnect once.
- `project.save()` on a project this size can exceed the 30s MCP client timeout — that's not a failure
  signal by itself, verify via `get_td_status` (new build number) before assuming it didn't complete.

## Where to place it in PatchDeck's network

This brief doesn't know PatchDeck's live network structure (not documented in its `AGENTS.md`/`CLAUDE.md`).
Per PatchDeck's own project rules: run `query_network` on `/` first to find the real root, then place a
new dedicated COMP (e.g. `gaia_agent`, sibling-level, not buried inside an unrelated existing chain) —
same "dedicated COMP, not merged into existing modules" choice TD-Gaia made for its own `Bridge` COMP.
Follow PatchDeck's own network-layout rules (200-unit grid, annotate the group) when placing it.

## Source-of-truth references (for anything this brief doesn't cover)

- `GAIA_INTERFACE.md` at the root of the `TD4Gaia` repo (`/Users/maurospagnoli/Documents/TD/Agent`) —
  cross-session contract + changelog between the Gaia/Core side and the TD/Mac side. Worth a read if
  something here looks stale.
- The `gaia` repo's `minipc/touchdesigner/GAIA_TD_INTEGRATION.md` — canonical OSC/MQTT schema
  documentation maintained from the Gaia/Core side.

## Not covered here (deliberately out of scope)

- The `gaia_agent`/`gaia_control` **device-registration protocol** (`gaia/device/{id}/status`,
  making this TD instance show up in Gaia's Pi Manager) — that's a device/service-plane concern, not
  needed just to *receive* feeds. Only build it if PatchDeck needs to appear as a controllable Gaia
  device.
  **Update 2026-08-18, later same day: the user does want this built now** — it's also the
  prerequisite for direct mocap ingest (see `GAIA_DEVICE_AGENT_BRIEF.md`, next to this file, for the
  full spec and a naming-collision risk that needs resolving before picking a `device_id`).
- Any actual visual effects consuming this data — per the user's direction, ingest first, decide what
  to build on top of it afterward.
