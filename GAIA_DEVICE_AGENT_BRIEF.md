<!-- Prepared by Claude (TD-Gaia/Agent session), 2026-08-18. Follow-up to GAIA_AGENT_BRIEF.md. -->

# PatchDeck Gaia device-agent + direct mocap — build brief

## Why this exists

The MQTT ingest client built from `GAIA_AGENT_BRIEF.md` works (subscribes `gaia/td/canvas`,
`gaia/brain/state`, `gaia/brain/dream`). But that brief **deliberately scoped out** the
`gaia_agent`/`gaia_control` device-registration protocol as "only if needed." The user has now hit
the consequence of that gap: PatchDeck never shows up as an online device in Gaia, and can't receive
direct mocap (`gaia/mocap/*`, OSC-only, never mirrored to MQTT — confirmed in the other brief).

**These are one gap, not two.** Mocap direct depends on device registration, not a separate feature:
TD-Gaia's own mocap redirect only works because `gaia_agent` first publishes this TD instance's
status (including its IP) to `gaia/device/{id}/status`. Gaia's mediapipe process reads that registry
to decide where to send OSC. No status publish → Gaia has no way to know PatchDeck exists as a mocap
destination, regardless of anything on the OSC side.

## Part 1 — Status publisher (`gaia_agent` equivalent)

Port TD-Gaia's proven pattern (`/project1/container1/Bridge/gaia_agent` in the TD4Gaia repo,
`/Users/maurospagnoli/Documents/TD/Agent`) rather than reinventing:

- **Native `mqttclientDAT`**, not `paho.mqtt.client`. TD's embedded Python has no pip; `paho` only
  ever worked on TD-Gaia because Envoy's venv happened to be on `sys.path` — an accidental runtime
  dependency that broke on any machine without Envoy enabled. The native DAT dispatches
  `onConnect`/`onMessage` on TD's main thread, no threading/queue machinery needed.
- Publish `gaia/device/{device_id}/status` periodically (a `time.time()`-throttled `tick()` in an
  Execute DAT `onFrameStart`, not a thread) with at least: `device_id`, `role`, `ip`, timestamp, and
  whatever heartbeat/health fields `gaia_device_agent.py` already sends for TD-Gaia (check that
  script in the `gaia` repo for the exact current payload shape — don't guess the schema).
- `ip` via the same UDP-connect trick already standardized across the `gaia` repo (`socket.socket
  (AF_INET, SOCK_DGRAM); s.connect(("8.8.8.8", 80)); s.getsockname()[0]`) — works with zero real
  internet reachability, avoids `gethostbyname(gethostname())` resolving to `127.0.0.1`.
- Subscribe to enable/disable/restart commands the same way `gaia_agent` does, if PatchDeck should be
  remotely controllable from Gaia's Pi Manager (confirm with the user whether that's wanted here, or
  status-only is enough for now).

### mqttclientDAT gotchas that will bite here too (verified on TD-Gaia)

- `dat.isConnected` is a **property**, not a method.
- `dat.publish(topic, payload, ...)` needs `payload` as **`bytes`** — `json.dumps(...).encode
  ('utf-8')`. This one is dangerous because it fails **silently**: no exception in `get_op_errors`,
  the only symptom is "this device never appears in the registry." If status publish looks wired but
  the device doesn't show up anywhere, manually re-invoke the publish function via `execute_python`
  to force the real traceback into view — don't trust `get_op_errors` alone for callback-DAT bugs.
- `storage()`/`fetch()` on a COMP **cannot hold live objects** (sockets, locks, threading.Event) —
  breaks `project.save()` silently by failing to pickle. Not an issue with the native-DAT approach
  (no live client object to store), but avoid reintroducing one.
- A `Toggle`-style Execute DAT "Start" parameter does not reliably survive a `.tox` externalization
  roundtrip. If a genuine app-launch trigger is needed, place that lifecycle DAT **outside** any
  Embody-tox-tracked subtree (project root), same fix used on TD-Gaia's `/gaia_startup`.
- Each independently-tox-tracked child COMP needs **its own** `save_externalization` call — a
  parent's save does not cascade into force-resaving an independently-tracked nested child. Check
  `.par.X.mode` (not just the value) after any restart to confirm an expression-mode par actually
  survived.

## Part 2 — device_id: a real naming conflict to resolve BEFORE building, not after

User's stated goal: PatchDeck sometimes runs on the same Mac as TD-Gaia (not in parallel), sometimes
on a different machine — wants a `patchdeck` suffix on the device_id so it's unambiguous in Gaia's
device list either way. That's the right call for the *registry/status* side.

**But there's a specific, unverified risk on the *mocap redirect* side that a suffix could break.**
Per TD-Gaia session notes from 2026-08-05/06 (12 days old, needs re-verification, not re-derivation
from memory): the `gaia` repo's `mediapipe_node.py` picks which device to redirect OSC mocap to by
checking `role == 'touchdesigner'` **AND** `device_id == f'td-{own_hostname}'` — an exact-string
match against a hardcoded `td-` prefix + the hostname of the machine running mediapipe, specifically
because mocap-direct only makes sense same-machine (redirecting OSC to a `localhost`-equivalent
target). If that matching code still works exactly this way, then:

- A device_id like `td-patchdeck-{hostname}` would **not** match `f'td-{hostname}'` and mocap would
  never redirect to PatchDeck, with no error anywhere — the same silent-failure shape as the two
  earlier bugs in this codebase (stale `OSC_HOST`, hardcoded device name in `MocapBridgeExt`).
- The registry-identity need (unambiguous `patchdeck` suffix) and the mocap-redirect need (exact
  `td-{hostname}` match) may be **in tension**, not compatible by default.

**Do not guess a resolution — read the current matching code first.** Before picking the final
`device_id` string:

1. Open the `gaia` repo (separate from PatchDeck and from TD4Gaia — check `reference_gaia_td_repos`
   memory or ask the user for its path) and find the current OSC-redirect matching logic (was in
   `pi/mediapipe/mediapipe_node.py` as of 2026-08-05/06, may have moved). Read what it actually
   compares now — this brief's description of it is a secondhand, 12-day-old account, not a live read.
2. If it's still an exact `f'td-{hostname}'` match with no room for a distinguishing suffix, that's a
   real product decision, not a code detail — surface it to the user rather than picking silently:
   either (a) Gaia's matching logic needs to accept a role/id convention that supports multiple
   TD instances per hostname (a Gaia-repo change, likely coordinated with whoever else works that
   repo — see the cross-repo git-race-condition lesson in `project_gaia_bridge_build` memory), or
   (b) PatchDeck's device_id keeps the exact `td-{hostname}` form for mocap purposes and a *separate*
   field (not the id) carries the `patchdeck` disambiguator for the registry/UI side.
3. Only after confirming which shape the redirect logic actually needs, wire `device_id` in the
   status payload to match it.

## Part 3 — OSC mocap ingest (once redirect is confirmed working)

- Mocap is OSC-only, never mirrored to MQTT (confirmed via live broker sniff, `GAIA_AGENT_BRIEF.md`).
- Needs an OSC In CHOP on whatever port the mediapipe redirect sends to. If PatchDeck and TD-Gaia
  might run **at the same time on the same Mac**, they cannot both bind the same OSC port (TD-Gaia
  uses UDP 7000) — confirm with the user or the `gaia` repo whether the redirect target port is
  fixed or configurable per-device before assuming 7000 is free to reuse.
- **Mocap channel addressing is unstable** (documented in `project_gaia_new_namespaces` memory):
  channel counts grow over a session, no automatic expiry on `oscinCHOP`, mixed zero-padding eras
  coexist on the same address family. Don't assume a fixed landmark-to-channel mapping — TD-Gaia's
  `MocapBridgeExt` works around this by tracking identity via **activity** (value changing between
  cooks) rather than literal address; reuse that defensive pattern rather than rediscovering it.
- TD-Gaia's face-tracking build (same memory file, "Face construction fix" section) also found that
  pooling all landmark points globally by activity produces a broken result when the data has
  sub-structure (anatomical regions) — a fixed per-region budget was needed. Worth knowing before
  building any mocap visualization on top of the raw ingest, not just the ingest itself.

## Scope check before starting

This TD-Gaia/Agent session cannot reach PatchDeck's live TD network (separate `.mcp.json`/Envoy
bridge). Building the actual operators needs a Claude Code session with working directory inside this
PatchDeck project folder. Start with `query_network` on `/` to find the live root and where the
existing MQTT ingest client already lives, then place the new `gaia_agent`-equivalent as a sibling
COMP (not merged into the ingest client) — same "dedicated COMP" pattern as TD-Gaia's own `Bridge`.
