# MERCURY CAD AI X — PROJECT TITAN

A CAD platform: **2D plan → AI → 3D → BIM → quantities → environment → digital twin**.

The geometry kernel, plan reader, IFC4 writer, generative engine and analysis
modules were written for this project. Only FastAPI is required to expose the
API; everything else uses the standard library.

---

## Getting started

```bash
pip install -r requirements.txt
uvicorn API.main:app --reload --port 8000
```

UI: `Frontend/index.html` · Interactive docs: `/docs` · Liveness: `/health`
Readiness: `/ready`

```bash
pytest -q
docker compose up --build
```

---

## What it does

**Designs.** Give it a brief — 110 m², three bedrooms — and simulated annealing
searches a slicing tree for the layout that best satisfies target areas,
proportions, orientation, daylight, adjacencies and plumbing grouping. The
output is a complete BIM project, not a picture.

**Reads plans.** Professional drawings represent a wall as two parallel lines:
the engine pairs them, merges collinear axes *across openings*, then extends
them to their intersections.

**Extracts rooms.** Wall axes form a planar arrangement: split at
intersections, weld vertices, prune dangling edges, traverse half-edges. No
flood fill.

**Quantifies.** Take-off where every quantity carries its formula, cost
estimate per trade, schedule with critical path, embodied carbon (A1-A3) with
levers ranked by actual saving, energy model across six climates.

**Exports.** IFC4 with base quantities, OBJ, glTF 2.0, SVG, JSON.

**Observes.** Sensors are bound to rooms of the BIM model: a deviation in a
large occupied volume is flagged more severe than the same in a plant room.

---

## Honest limits

- The **energy model** is a static monthly method, not an hourly dynamic
  simulation. No thermal inertia, occupancy scenarios or solar masks. It is not
  a regulatory calculation.
- **Vision models** have a real architecture and API but **fake weights**: they
  demonstrate the pipeline, they do not yet recognise anything.
- **Structure** and **MEP** modules are sketch-stage pre-sizing, not a
  substitute for engineering calculations.
- **Construction site**, **territory** and **augmented reality** groups are
  scaffolded: interfaces exist, engines remain to be written.
