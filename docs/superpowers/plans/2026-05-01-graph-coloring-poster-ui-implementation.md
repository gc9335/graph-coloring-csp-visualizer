# Graph Coloring Poster UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the static graph-coloring visualizer into an academic-poster-style defense page while preserving the existing solver playback and interaction behavior.

**Architecture:** Keep the current static stack (`index.html`, `styles.css`, `app.js`, `solver.js`) and avoid changing solver logic. Rebuild the page around a stronger semantic layout, fix all mojibake Chinese copy at the source, and retune rendering/styling so the graph stage, timeline, pseudocode, domain matrix, and search tree feel like one coherent presentation board.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript modules, existing Node-based syntax checks and Python-based regression tests.

---

### Task 1: Protect Frontend Chinese Copy

**Files:**
- Create: `tests/test_frontend_copy_integrity.py`
- Modify: `index.html`
- Modify: `app.js`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path


FILES = [
    Path("index.html"),
    Path("app.js"),
]

BAD_MARKERS = ["鍥", "銆", "閫", "鐫€", "姝ラ", "绠楁硶"]


def test_frontend_copy_has_no_mojibake_markers():
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        for marker in BAD_MARKERS:
            assert marker not in text, f"{path} still contains mojibake marker: {marker}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python tests/test_frontend_copy_integrity.py`

Expected: FAIL because `index.html` and `app.js` still contain mojibake Chinese strings.

- [ ] **Step 3: Write minimal implementation**

Replace mojibake labels in `index.html` and `app.js` with normalized Chinese text for:

- page title
- hero title and summary
- control labels and buttons
- panel titles and descriptions
- event labels and metric copy

- [ ] **Step 4: Run test to verify it passes**

Run: `python tests/test_frontend_copy_integrity.py`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_frontend_copy_integrity.py index.html app.js
git commit -m "test: protect frontend chinese copy integrity"
```

### Task 2: Rebuild the Poster-Style Layout

**Files:**
- Modify: `index.html`
- Modify: `styles.css`

- [ ] **Step 1: Write the failing structure check**

Use the copy-integrity test file and extend it with required layout hooks:

```python
REQUIRED_IDS = [
    "hero-metrics",
    "graph-stage",
    "timeline",
    "pseudocode-list",
    "domain-matrix",
    "search-tree",
]


def test_frontend_contains_required_layout_hooks():
    html = Path("index.html").read_text(encoding="utf-8")
    for hook in REQUIRED_IDS:
        assert f'id="{hook}"' in html, f"missing layout hook: {hook}"
```

- [ ] **Step 2: Run test to verify it passes before refactor**

Run: `python tests/test_frontend_copy_integrity.py`

Expected: PASS on structure hook assertions so we can safely refactor around existing mount points.

- [ ] **Step 3: Rewrite the HTML layout**

Implement the poster structure in `index.html`:

- hero banner with strong Chinese title and concise abstract
- variant strip under hero
- compact control panel
- first band: graph stage + explanation panel
- second band: timeline + pseudocode
- third band: domain matrix + search tree

Keep all existing mount `id`s so `app.js` continues to bind without large rewrites.

- [ ] **Step 4: Rebuild the visual system**

Implement in `styles.css`:

- new warm-paper background and poster variables
- stronger title typography
- refined panel shells and spacing
- new layout grid classes for the three presentation bands
- timeline card styling
- pseudocode board styling
- matrix and tree container polish
- improved control bar/button styling
- responsive stacking behavior

- [ ] **Step 5: Run syntax and structure checks**

Run:

```bash
python tests/test_frontend_copy_integrity.py
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add index.html styles.css tests/test_frontend_copy_integrity.py
git commit -m "feat: rebuild poster-style frontend layout"
```

### Task 3: Update Rendering Copy and Presentation Behavior

**Files:**
- Modify: `app.js`

- [ ] **Step 1: Write the failing JavaScript syntax check expectation**

Run:

```bash
node --check app.js
```

Expected: If any template-string or text rewrite introduces syntax issues, this command fails and blocks the task.

- [ ] **Step 2: Update the rendering layer**

Implement in `app.js`:

- normalized Chinese event labels
- normalized color names and graph descriptions
- cleaner hero metric labels
- stronger stage caption text
- timeline and explanation copy that matches the new academic-poster tone
- preserve current graph/tree drag and playback interactions

- [ ] **Step 3: Verify JavaScript syntax**

Run:

```bash
node --check app.js
node --check solver.js
```

Expected: both PASS

- [ ] **Step 4: Commit**

```bash
git add app.js
git commit -m "feat: refresh frontend rendering copy and presentation"
```

### Task 4: Full Verification and Visual Smoke Test

**Files:**
- Test: `tests/test_frontend_copy_integrity.py`
- Test: `tests/test_graph_coloring_core.py`
- Verify: `index.html`, `styles.css`, `app.js`

- [ ] **Step 1: Run automated checks**

Run:

```bash
python tests/test_frontend_copy_integrity.py
python tests/test_graph_coloring_core.py
node --check app.js
node --check solver.js
```

Expected: all PASS

- [ ] **Step 2: Launch a local static preview**

Run:

```bash
python -m http.server 4173
```

Expected: local static site serves without build tooling.

- [ ] **Step 3: Visual smoke test in browser**

Check:

- Chinese title and controls render correctly
- hero, graph stage, timeline/pseudocode, matrix/tree form the new poster hierarchy
- timeline scroll remains internal
- tree drag and zoom still work
- main graph still renders and plays through events

- [ ] **Step 4: Commit**

```bash
git add index.html styles.css app.js tests/test_frontend_copy_integrity.py
git commit -m "chore: verify poster-style UI redesign"
```

## Self-Review

Spec coverage:

- Poster aesthetic: covered by Task 2 visual system rewrite
- Layout restructure: covered by Task 2 HTML/CSS changes
- Chinese normalization: covered by Task 1 and Task 3
- Interaction preservation: covered by Task 3 and Task 4 smoke test
- Static deployment compatibility: preserved by keeping the static stack and using a plain HTTP preview in Task 4

Placeholder scan:

- No `TODO`/`TBD`
- Every task includes concrete files and commands
- Verification commands are explicit

Type consistency:

- Existing DOM mount ids stay unchanged where JavaScript depends on them
- Tests reference exact filenames and ids already present in the app
