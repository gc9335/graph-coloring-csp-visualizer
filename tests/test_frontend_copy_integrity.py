from pathlib import Path


FILES = [
    Path("index.html"),
    Path("app.js"),
]

BAD_MARKERS = ["鍥", "銆", "閫", "鐫€", "姝ラ", "绠楁硶"]
REQUIRED_IDS = [
    "hero-metrics",
    "graph-stage",
    "timeline",
    "pseudocode-list",
    "domain-matrix",
    "search-tree",
]


def test_frontend_copy_has_no_mojibake_markers():
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        for marker in BAD_MARKERS:
            assert marker not in text, f"{path} still contains mojibake marker: {marker}"


def test_frontend_contains_required_layout_hooks():
    html = Path("index.html").read_text(encoding="utf-8")
    for hook in REQUIRED_IDS:
        assert f'id="{hook}"' in html, f"missing layout hook: {hook}"


if __name__ == "__main__":
    test_frontend_copy_has_no_mojibake_markers()
    test_frontend_contains_required_layout_hooks()
    print("test_frontend_copy_integrity.py passed")
