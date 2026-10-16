# Plancia Video Service — Architecture Proposal

**Status:** Proposed architecture — proof of concept pending  
**Scope:** Video Service only.

## Objective

Develop a standalone service that receives live video sources over the local network and provides low-latency previews to Plancia through a browser.

The service must be accessible from multiple PCs and tablets without requiring dedicated video software on client devices.

## Proposed architecture

- **Host:** Dedicated Windows PC on the same LAN as TouchDesigner / TD4PatchDeck and Resolume.
- **Video ingestion:** GStreamer with the NDI plugin.
- **Processing:** Video conversion, downscaling and low-latency H.264 encoding.
- **Browser delivery:** WebRTC.
- **Service API:** HTTP API for source discovery, preview sessions and status; HTTP/WebSocket signaling for WebRTC.
- **Clients:** Plancia running in a browser on PCs and tablets.
- **Network:** LAN-first. Keep the preview service independent from critical show output.

## References

- GStreamer NDI plugin: https://gstreamer.freedesktop.org/documentation/ndi/index.html
- GStreamer WebRTC: https://gstreamer.freedesktop.org/documentation/webrtc/
- TD4PatchDeck: https://github.com/vsvisualsubstance-source/TD4PatchDeck
- TD4DMX: https://github.com/vsvisualsubstance-source/TD4DMX
- Gaia: https://github.com/vsvisualsubstance-source/gaia

## Initial preview profile

Starting values to validate experimentally; performance is not guaranteed:

- Resolution: 640 × 360
- Frame rate: 15–20 fps
- Codec: H.264
- Bitrate: approximately 400–800 kbit/s per preview
- Audio: disabled initially
- Priority: minimum practical end-to-end latency, even at reduced image quality

## Proposed API

- `GET /api/sources` — list available sources.
- `GET /api/sources/{id}` — retrieve source details and status.
- `POST /api/previews` — request a preview session.
- `GET /api/previews/{id}/status` — retrieve preview status.
- `DELETE /api/previews/{id}` — stop a preview session.

The API and WebRTC signaling protocol are preliminary and may change during prototyping.

## Implementation plan

### Phase 1 — Proof of concept

1. Install GStreamer and verify the NDI plugin on Windows.
2. Receive one NDI source from TouchDesigner.
3. Process and encode the video.
4. Deliver the stream through WebRTC.
5. Display it in a browser on a PC and a tablet simultaneously.
6. Measure latency, stability, bandwidth and resource usage.

### Phase 2 — Service foundation

- Implement source discovery and management.
- Implement the HTTP API and WebRTC signaling.
- Add connection monitoring, reconnection handling and diagnostics.
- Support multiple browser clients.

### Phase 3 — Plancia integration

- Integrate the browser preview component into Plancia.
- Keep the UI independent of the underlying media pipeline.
- Expose source and preview status to Plancia.

### Phase 4 — Multiple sources

- Add Resolume as an additional NDI source.
- Test multiple simultaneous previews.
- Measure CPU/GPU load, network bandwidth and latency.

## Proof-of-concept acceptance criteria

- One NDI source from TouchDesigner is visible in a browser without a desktop player.
- Two browser clients can view the preview simultaneously.
- Preview service restart or disconnection does not interrupt TouchDesigner, Resolume, DMX, laser control or other show-critical processes.
- Latency and resource usage are measured and documented.

## Technical questions to validate

- Compatibility between the selected Windows GStreamer distribution, NDI plugin and required NDI runtime.
- Actual plugin element names, properties and source-discovery behavior.
- Best low-latency GStreamer-to-WebRTC pipeline.
- Efficient delivery of the same encoded source to multiple clients.
- Whether a separate media gateway is necessary; avoid adding one unless testing demonstrates a clear benefit.
- Service language/runtime, to be selected after the end-to-end prototype.
- LAN access and Windows Firewall configuration first; HTTPS and remote access can be considered separately.

## Critical isolation requirement

The Video Service is a monitoring component, not a critical show-control dependency. A service crash, network interruption or restart must not interrupt TouchDesigner, Resolume, DMX, laser control or other show-critical processes.

## Scope boundary

This proposal covers only the Plancia Video Service: video ingestion, preview distribution, API and diagnostics. It does not define or implement the broader show-control architecture.

## Intended repository placement

Primary: `vsvisualsubstance-source/TD4PatchDeck`  
Path: `docs/architecture/plancia-video-service.md`

Add a short reference from Gaia to the same document after publication, rather than maintaining duplicate specifications.
