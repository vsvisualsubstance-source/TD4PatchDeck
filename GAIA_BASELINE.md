<!-- Verified live from PatchDeck's own MCP session, 2026-08-31. This is the PatchDeck-side half
of a cross-repo "punto zero" checkpoint (Gaia core / TD4Gaia / PatchDeck+DMX). -->

# Gaia Integration Baseline (punto zero) — 2026-08-31

## Scope

This is the PatchDeck-side checkpoint of a shared baseline across the three Gaia-connected
projects: **Gaia (core)**, **TD4Gaia** (`/Users/maurospagnoli/Documents/TD/Agent`, a separate
machine/repo not reachable from this session), and **PatchDeck** (this repo, + its DMX agent).
The Gaia (core) side of the checkpoint was done separately in that project, not here. Purpose:
a single verified snapshot of what each side currently exposes over MQTT, instead of drifting
brief docs (`GAIA_AGENT_BRIEF.md`, `GAIA_DEVICE_AGENT_BRIEF.md`) going stale.

## Devices registered from this repo

PatchDeck runs **two independent Gaia Agent Universale instances**, each its own MQTT identity
on the native `mqttclientDAT` (never paho — see `gaia_client/gaia_device_agent.py` docstring).
Same protocol as the Pi/OPS Gaia agents: `gaia/device/{id}/status` (heartbeat, retained),
commands on `gaia/device/{id}/command` + `gaia/device/all/command`
(`action`: `enable`/`disable`/`restart`/`set`).

### 1. `gaia_client` (`op.Gaia`, family `patchdeck`)

- `device_id`: `td-pd-macmauro` — `stanza`: `salotto`
- Ingests: `gaia/brain/state`, `gaia/canvas/*` (`topic_brainstate.py` / `topic_canvas.py`),
  direct mocap OSC (`Mocapingest`)
- Exposes control (PatchDeck is the controllable device here, not just an ingest client),
  registered by `PATCHDECK/gaia_services/patchdeck_services.py`:
  - **78 on/off services**: `deck_a`, `deck_b`, `load_x{1..38}_{a|b}` — load/clear/status of the
    38 `PATCHES` onto Deck A/B
  - **5 continuous params** (added 2026-08-31): `edge`, `feedback`, `fb_scale`, `fb_blur`,
    `mirror` — the first 5 POST_FX knobs on `control_ui` (custom pars `Fx1..Fx5`, 0..1 float; see
    `PATCHDECK/PATCHES/POST_FX/fx_lables.tsv` for the full `FX1..FX8` label map, only the first 5
    are exposed — `FX6/7/8` = Brightness/Black Lvl/Strobo, not requested)
  - Retained matrix at `gaia/devices/td-pd-macmauro/patchdeck_matrix` (`services` + `fx_params`
    with label/range, so a consumer doesn't need to guess the name→label mapping)

### 2. `gaia_dmx_client` (`op.GaiaDmx`, family `dmx`)

- `device_id`: `td-pddmx-macmauro` — `stanza`: `salotto`
- Independent identity dedicated only to `PATCHDECK/DMX/dmx_audio_chase` (single rig, `'a'`)
- Exposes (`gaia_dmx_client/dmx_services.py`, schema mirrors the standalone DMX V8 project's
  `gaia_client/dmx_services.py` verbatim): **3 services** (`dmx_a_kick_enable`,
  `dmx_a_use_file_input`, `dmx_a_apply_fixture_profile`) + **27 continuous/menu/color params**
  (dimmer curve, color curve/speed/phase, kick tuning, fixture profile, 5 custom palette colors)
- Retained matrix at `gaia/devices/td-pddmx-macmauro/dmx_matrix`

## Broker

`tcp://192.168.1.142:1883` (LAN) — resolved via Beacon Auto-Discovery on `gaia_client`
(`Beacondiscovery=True`); confirmed live 2026-08-31
(`Beaconstatus: auto: 192.168.1.142 (beacon @ core-node-0, ...)`).

## Verified live, this session (2026-08-31)

- Both devices connected (`Connectionstatus` / `Deviceagentstatus` = `connected`)
- No cook/script errors under `/gaia_client` or `/gaia_dmx_client`
- FX param round-trip tested end-to-end through `_apply_command({"action":"set",
  "param":"fb_scale","value":...})` — correctly writes `control_ui.par.Fx3` and restores

## Known gaps (PatchDeck side)

- Direct mocap ingest (`Mocapingest=True`) is receive-only; not exercised against a live Gaia
  mocap feed in this session
- `fx_params`/DMX param matrices advertise label + numeric range only — no menu/step metadata
  yet, add it if TD4Gaia's UI generator needs more than a plain slider

## Out of scope here — Gaia (core) side

The **"nursery"** item belongs to the Gaia (core) project, not PatchDeck — it isn't part of this
repo's tree and wasn't investigated in this session. Flagged here only so this baseline doesn't
silently omit it: reconcile it against whichever checkpoint exists on the Gaia (core) side.
