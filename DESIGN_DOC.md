# Sriracha Sketcher — Technical Design Doc v1.0

**Owner:** Team Vietnam
**Date:** Nov 13, 2025  
**Status:** Draft for review

---

## 1) Summary
Build an AI-powered “sauce plotter” that converts a user text prompt into a physical drawing with Sriracha on a plate of food. A 2-axis motion platform (X-Y gantry) with a sauce-dispensing end effector is driven by an ESP32. A web UI lets users describe what they want; a backend iteratively generates SVG line art with an LLM generator and a VLM critic, then compiles the SVG into low-level movement instructions streamed to the ESP32 over WebSockets.

---

## 2) Goals & Non-Goals
**Goals**
- Convert prompts into **stroke-only** SVG suitable for plotting with hot sauce (few lifts, clean contours).
- Accurate, repeatable motion with controllable sauce flow (start/stop/ramp) and minimal smearing.
- React chat UI with simulation preview and job controls (start/pause/stop).
- Iterative generator→critic loop to converge on print-ready SVG.
- Safety: endstops, E-Stop, timeouts, and cleaning mode.

**Non-Goals (v1)**
- Photorealistic shading or complex hatching.
- Multi-color sauces.
- Vision feedback during printing (camera alignment is a v2 idea).

---

## 3) System Architecture

```
[ User ]
│
▼
React UI (Next.js/React) ─── HTTP/WS ──> FastAPI Backend (Uvicorn, asyncio)
│
├─ LLM/VLM Orchestrator  ──> OpenAI APIs (text→SVG, judge)
│
├─ SVG Normalizer & Toolpath Compiler (Python)
│
├─ Simulation Renderer (headless) → judge context images
│
├─ Device Manager/Streamer → WS → ESP32 Firmware (C++)
│                               ▲            │
│                               └ telemetry ─┘
│
├─ Storage: Postgres (jobs/devices/runs)
└─ Artifacts: MinIO/S3 (SVG/PNG/SSG), Redis (queues) [opt]
```

**Key Services**
1. **React UI**: Chat, iteration progress, preview gallery, device controls & status HUD.
2. **FastAPI Backend**: Async orchestration, SVG → toolpath compilation, device streaming, persistence.
3. **LLM/VLM Loop**: Generator (SVG) + Judge (image critique) with heuristic pre/post filters.
4. **Device Manager**: Maintains ESP32 WS sessions, heartbeats, retries, and resume on reconnect.
5. **Persistence**: Postgres for metadata; object storage for SVG/PNG/SSG artifacts.

---

## 4) Hardware Design

### 4.1 Mechanical
- **Platform**: X-Y gantry (GT2 belts, 20-tooth pulleys) spanning a dinner plate (Ø ~240–280 mm).
- **Axes**: Dual X motors (X1/X2) for squaring; single Y motor.
- **End Effector**: Fixed Z standoff ~2–4 mm above surface; nozzle quick-release for cleaning.
- **Dispenser (v1 options)**:
  - **Servo Squeeze** (simple, cheap; nonlinear flow).
  - **Peristaltic Pump** (recommended v2; smoother start/stop, food-safe tubing).

### 4.2 Electronics
- **Controller**: ESP32-WROOM (Wi-Fi).
- **Drivers**: TMC2209 (preferred for quiet/smooth) or A4988 (budget).
- **Actuator**: Servo (PWM) or DC pump (PWM via MOSFET + flyback).
- **Power**: 12–24 V for steppers; 5 V rail for ESP32/servo.
- **Sensors**: Endstops X1, X2, Y; optional plate-present switch.
- **E-Stop**: Latching button cutting motor/actuator power.

### 4.3 Kinematics & Sizing
- **Steps/mm** (1.8° motor, 16× microstep, GT2 20T): 200 * 16 / (20 * 2) = **80 steps/mm**.
- **Initial motion limits**: travel 50 mm/s, drawing 10–20 mm/s, accel 600–1000 mm/s².

### 4.4 Food Safety & Cleanability
- Food-contact parts: stainless/food-grade plastic/silicone. Electronics shielded. “Clean” mode to purge.

---

## 5) Firmware (ESP32)

### 5.1 Responsibilities
- Parse a line-oriented motion protocol (**SSG**, “Sauce Simple G-code”) over WebSocket.
- Maintain a motion planner queue (lookahead, accel/cornering).
- Drive X1/X2/Y steppers; keep gantry square.
- Control sauce flow (PWM) with ramp-in/out and min on/off dwell.
- Report status/telemetry; enforce limits; handle E-Stop & faults.

### 5.2 State Machine
- **BOOT → IDLE**
- **HOMING** (X1, X2, Y; auto-squaring)
- **READY**
- **PRINTING**
- **PAUSED**
- **CLEANING**
- **ERROR** (limit, stall, comms, watchdog)

### 5.3 Protocol (WebSocket)
**Commands (SSG)**
```
N G0 X Y F       ; rapid (sauce off)  
N G1 X Y F       ; draw (sauce on if flow>0)  
N M3 S                            ; set flow duty (0–100)  
N M5                                   ; sauce off  
N G28                                  ; home all (auto-squaring)  
N M114                                 ; report position  
N M408                                 ; report status JSON
```

**Acks/Status**
```
ok N123  
busy q=28 state=PRINTING  
err N124 code=LIMIT  
telemetry {“pos”:{“x”:..,“y”:..},“flow”:..,“q”:..}
```

**Flow control**: Sliding window (e.g., 32 in-flight lines). Ack each line; host retransmits on timeout. 1 s heartbeat.

### 5.4 Motion Planner
- Trapezoidal w/ cornering velocity; 16–64 segment lookahead.
- Only G0/G1 in v1; arcs tessellated on host.
- Flow ramps synchronized with feed changes; on/off guard 50–100 ms.

### 5.5 Homing & Squaring
- Home X1 and X2 independently to X-min; back off; slow re-home for squaring; set shared X=0; home Y.

### 5.6 Firmware Language & SDK: **C++ vs MicroPython**
**Recommendation:** Use **C++** (Arduino Core or ESP-IDF) for v1 firmware; keep high-level logic in Python on the FastAPI backend.

**Why C++ (ESP-IDF/Arduino):**
- Deterministic step timing and lower jitter at higher speeds/accelerations.
- Mature libraries (AccelStepper/TMC), robust async networking, ISR/timer control.
- Better separation of planner tick (real-time) vs network tasks (FreeRTOS).

**When MicroPython could fit:**
- Low-speed demos/education where simplicity > performance.
- Single-motor experiments without tight timing constraints.

**Architecture (C++ on ESP-IDF/Arduino)**
- **Task A (Planner Tick):** High-prio timer/ISR drives step generation & flow PWM updates.
- **Task B (WS Network):** Receives lines, validates N#, pushes to a FreeRTOS queue.
- **Task C (Control):** State machine, endstop debouncing, config endpoints.

**Minimal parsing sketch (C++):**
```cpp
// on WS text frame:
parse_line(buf); // expects "N123 G1 X10.00 Y20.00 F600"
if (seq_ok) enqueue_move(cmd);
send_ok(seq);
```



## 6) Backend (FastAPI)

### 6.1 Stack & Services  
- Stack: Python 3.11, FastAPI, Uvicorn, Pydantic v2, Pillow/CairoSVG (raster), Shapely/pyclipper (paths), NumPy.  
- Services:  
    - LLM/VLM Orchestrator: generator→critic loop to produce print-ready SVG.  
    - SVG Normalizer: flatten transforms, remove fills, stroke-only, Bézier→polylines.  
    - Toolpath Compiler: polylines→SSG (ordering, feed/flow planning, plate clipping).  
    - Device Manager/Streamer: WS sessions, acks/retries, telemetry, resume.  
    - Simulation Renderer: “sauce physics lite” images for preview and judge context.  
    - Persistence: Postgres (jobs/devices/runs); MinIO/S3 for artifacts; optional Redis.

### 6.2 API (external/internal)  
- ```POST /jobs {prompt}``` 
- ```GET /jobs/{id} → job & artifacts```
- ```POST /devices/{id}/stream {ssg}```
- ```WS /devices/{id} (bi-dir stream)```
- ```POST /devices/{id}/home|pause|resume|stop|clean```
- ```GET /devices / GET /devices/{id}```

### 6.3 Orchestration Model  
- HTTP starts a job; async background task runs gen→critic loop → compile → stream.  
- Per-device queue/backpressure; reject if busy unless force=true.  
- Persist svg_norm, sim images, ssg, and last acked N for resume.

### 6.4 Project Layout
```
backend/  
  app/  
    main.py            # FastAPI app/routers/startup  
    deps.py            # config/env  
    models.py          # Pydantic models  
    db.py              # Postgres  
    storage.py         # S3/MinIO helpers  
    orchestrator/  
      loop.py          # generator→critic  
      judge.py         # VLM rubric  
      normalize.py     # SVG cleanup  
      simulate.py      # rasterize/physics-lite  
      compile.py       # toolpath→SSG  
    devices/  
      manager.py       # WS sessions, heartbeats  
      streamer.py      # sliding window, acks  
    api/  
      jobs.py          # /jobs  
      devices.py       # /devices  
  tests/  
  Dockerfile  
  pyproject.toml
```

### 6.5 Deployment  
- Dev: Docker Compose (FastAPI, Postgres, MinIO, Redis [opt]).  
- Prod: same + Prometheus/Grafana; volumes; reverse proxy (Traefik/Caddy) if off-LAN.



## 7) Prompt → SVG (Generator/Critic Loop)

### 7.1 Generator Constraints  
- Stroke-only vector; no fills. Max paths: 100; max total length ~3 m.  
- Avoid features < 2 mm; no self-intersections if possible.  
- Fit within 220×220 mm (or plate profile); centered; single color.

### 7.2 Loop
```
for attempt in 1..K (e.g., K=6):  
  prompt' = base_prompt + critic feedback  
  svg = LLM_generate_svg(prompt')  
  svg_norm = normalize(svg)  
  sim_img = simulate(svg_norm)  
  score, feedback = VLM_judge(sim_img, rubric)  
  if score >= PASS: break  
select best_by(score, penalties)
```

### 7.3 Judge Rubric (JSON)  
- Legibility (0–5), Stroke continuity (0–5), Printability (0–5), Aesthetics (0–5).  
- Return: {score:int, pass:bool, issues:[...], suggestions:[...]}.

### 7.4 Heuristic Pre-Filter  
- Reject paths < 4 mm; min segment length 0.3 mm; vertices ≤ 10k; inflate/simplify tiny loops.

### 7.5 Safety Filters  
- Block disallowed content; sanitize SVG (no external refs/scripts).



## 8) React Frontend  
- Chat flow with streaming updates from the iteration loop.  
- Preview: strokes/travels/sauce simulation overlays.  
- Controls: device select, home, start, pause/resume, stop, clean, jog.  
- Status HUD: state, queue depth, ETA, current line, flow %, WS health.  
- History: browse/reprint jobs.



## 9) Networking & Protocol Details  
- Discovery: mDNS or manual IP.  
- Transport: WebSocket ws://<esp-ip>/ws, ≤256 B per line; chunk jobs.  
- Reliability: Sequence numbers (N), sliding window (32), ack/timeout (~250 ms), heartbeat (1 s).  
- Security: LAN-only default; optional token auth; CORS pinned to UI origin.



## 10) Calibration & Tuning  
1. Homing check (gantry squaring).  
2. Steps/mm: 100 mm move → measure → adjust.  
3. Flow curve: ladders at S=20/40/60/80 at constant speed → measure line width.  
4. Speed tuning: raise F until artifacts; back off 20%.  
5. Nozzle height: shim to 2–4 mm standoff.  
6. Plate profile: center & radius; save per device.



## 11) Error Handling & Safety

### 11.1 Fault Taxonomy  
- Motion: endstop hit during print; stall; planner underrun; over-speed.  
- Comms: WS disconnect; ack timeout; out-of-order/dup; parse/CRC errors.  
- Flow: actuator stuck on/off; rapid toggling; purge failure/drip risk.  
- Thermal/Power: driver over-temp; brownout; E-Stop.  
- Content: unprintable SVG (tiny features/vertex explosion); disallowed prompt.

### 11.2 Interlocks & Limits  
- Hardware: physical E-Stop; endstops X1/X2/Y; conservative driver current.  
- Software: soft travel limits; refuse commands outside plate; cap queue depth; max job duration and path length.  
- Flow safety: min on/off dwell; duty cap; automatic sauce-off on PAUSE/ERROR/DISCONNECT.

### 11.3 Watchdogs & Safe States  
- Firmware watchdog kicks on planner tick; on trip enter ERROR until homed.  
- Heartbeat from host every 1 s; miss 3× → auto-pause, sauce off; retain last acked N.  
- Power/Link loss:  
- Firmware halts motion and sauce, remembers last completed N.  
- On reconnect, host queries M408 to learn last N; resume at N+1 after re-arming (user confirmation if sauce present).  
- If homing lost or endstop was hit → require G28 before resume.

### 11.4 Exceptions & Retries  
- Ack timeout: retry line up to 3×; persistent failure → PAUSE and surface to UI.  
- Parse error: firmware replies err N code=PARSE; host fixes or aborts job.  
- Limit/E-Stop: immediate sauce off; planner flush; transition to ERROR; require homing.

### 11.5 Logging & Observability  
- Firmware telemetry: pos, state, queue depth, flow, faults (codes).  
- Backend: structured logs per job/device; metrics (lines/s, retries, critic iterations).  
- Retention: artifacts & logs per job; exportable for debugging.



## 12) Testing & Validation

Unit: SVG parser, tessellator, compiler, protocol framing.  
Integration: ESP32 simulator (loopback); real device dry run (pen on paper).  
Acceptance (MVP):  
- Prompt “cat outline” prints ≤3 min; recognizable at 0.5 m.  
- Corner overshoot ≤0.5 mm at 10 mm/s.  
- Cleaning cycle finishes ≤60 s with no drips.



## 13) Milestones  
	1.	M0: ESP32 WS echo + jog; homing & endstops.  
	2.	M1: SSG → motion with pen; preview simulator in UI.  
	3.	M2: Single-pass generator → usable SVGs.  
	4.	M3: VLM critic loop + heuristics.  
	5.	M4: Sauce dispenser & flow calibration.  
	6.	M5: Safety hardening; E-Stop; cleaning; MVP demo.



## 14) Implementation Notes & Pseudocode

### 14.1 FastAPI — Jobs & Background Orchestration

# app/api/jobs.py
```
from fastapi import APIRouter, BackgroundTasks  
from app.orchestrator.loop import run_job

router = APIRouter()

@router.post("/jobs")
async def create_job(req: dict, bg: BackgroundTasks):
    job_id = await save_job_shell(req["prompt"])
    bg.add_task(run_job, job_id)  # generator→critic → compile → stream
    return {"job_id": job_id}
```

# app/orchestrator/loop.py
```
async def run_job(job_id: str):
    prompt = await load_prompt(job_id)
    best = None
    feedback = []
    for k in range(6):
        svg = await llm_generate_svg(prompt, feedback)
        svg_norm = normalize(svg)
        sim_img = simulate(svg_norm)
        score, fb = await vlm_judge(sim_img)
        if best is None or score > best.score:
            best = (svg_norm, score, fb)
        if score >= PASS: break
        feedback = fb.get("suggestions", [])
    ssg = compile_toolpath(best[0])
    await store_artifacts(job_id, svg_norm=best[0], ssg=ssg)
    await stream_to_device(job_id, ssg)
```

### 14.2 FastAPI — Device Streaming (sliding window)

# app/devices/streamer.py
```
WINDOW = 32  
ACK_TIMEOUT = 0.25

async def stream_to_device(job_id: str, ssg_lines: list[str], ws):
    next_n = 1
    inflight = {}
    for line in ssg_lines:
        pkt = f"N{next_n} {line}"
        await ws.send(pkt)
        inflight[next_n] = now()
        next_n += 1
        while len(inflight) >= WINDOW:
            typ, payload = await ws.recv(timeout=ACK_TIMEOUT)
            if typ == "ok":
                inflight.pop(payload.seq, None)
            elif typ == "err":
                # retry or pause based on code
                await handle_error(payload)
            else:
                # telemetry/busy heartbeat
                pass
        # retry any timed-out lines
        for n, t0 in list(inflight.items()):
            if now() - t0 > ACK_TIMEOUT:
                await ws.send(rebuild_line(n))
                inflight[n] = now()
```

### 14.3 Firmware — SSG parse/ack (C++ sketch)
```
void handleWSMsg(const char* data) {
  // Expect: "N123 G1 X10.00 Y20.00 F600" or "N234 M3 S60"
  Parsed p;
  if (!parse_ssg_line(data, &p)) {
    ws.printf("err N%d code=PARSE\n", p.seq);
    return;
  }
  if (!seq_ok(p.seq)) {
    ws.printf("err N%d code=SEQ\n", p.seq);
    return;
  }
  if (!enqueue(p)) { // planner queue full
    ws.printf("busy q=%d state=%s\n", q_depth(), state_str());
    return;
  }
  ws.printf("ok N%d\n", p.seq);
}
```

### 14.4 Toolpath Compilation (Python)

```
paths = svg_to_paths(svg_norm)  
paths = tessellate(paths, max_err=0.2)          # adaptive subdivision  
paths = simplify(paths, epsilon=0.15)           # RDP simplify  
paths = order_paths(paths)                      # nearest-neighbor + 2-opt  
emit("G28")  
for p in paths:
    emit("M3 S{}".format(flow_for(p)))
    for x, y, f in segments(p):
        emit("G1 X{:.2f} Y{:.2f} F{:d}".format(x, y, f))
    emit("M5")
```



## 15) Risks & Mitigations  
- SVG quality → tight constraints, heuristics, critic loop, and preview.  
- Flow variability → calibration ladders; consider peristaltic pump in v2.  
- Viscosity/temp → pre-warm bottle (food-safe), or dynamic flow scaling.  
- Comms flakiness → sequence/acks/resume; LAN-only.  
- Messiness → drip tray, shields, mandatory clean cycle.



## 16) Open Questions  
1. End effector choice (servo vs peristaltic) for v1?  
2. Plate origin (center vs corner) & exact printable radius?  
3. Max print time target and path density trade-off?  
4. Driver choice vs noise budget (TMC2209 preferred)?  
5. Camera alignment (v2) worth planning hooks now?



## 17) Appendix

### 17.1 Example SSG (excerpt)
```
N1  G28                          ; home  
N2  M3 S60                       ; sauce on 60%  
N3  G1 X10.00 Y10.00 F600  
N4  G1 X50.00 Y10.00 F600  
N5  G1 X50.00 Y50.00 F480  
N6  M5                           ; sauce off  
N7  G0 X0.00 Y0.00 F3000  
N8  M114                         ; report pos
```

### 17.2 FastAPI WS Endpoint (sketch)
```
from fastapi import APIRouter, WebSocket  
router = APIRouter()

@router.websocket("/devices/{id}")
async def device_ws(ws: WebSocket, id: str):
    await ws.accept()
    register_device(id, ws)
    try:
        while True:
            msg = await ws.receive_text()
            route_or_log_telemetry(id, msg)
    except Exception:
        unregister_device(id)
```

### 17.3 Config JSON (firmware-served)
```
{
  "steps_per_mm": 80,
  "max_feed_draw": 600,
  "max_feed_rapid": 3000,
  "accel": 800,
  "plate": { "center": [0,0], "radius_mm": 110 },
  "flow_curve": [[20,1.5],[40,2.2],[60,2.8],[80,3.4]]  // duty→line width mm
}
```
**TL;DR on ESP32 language:** go **C++** (Arduino Core or ESP-IDF) for reliable, jitter-free motion; keep all AI/compilation logic in **Python/FastAPI**.