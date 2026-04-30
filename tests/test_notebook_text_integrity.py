import json
from pathlib import Path


NOTEBOOKS = [
    Path("code/colorfilling_su_60s.ipynb"),
    Path("code/colorfilling_su_300s.ipynb"),
    Path("code/colorfilling_su_600s.ipynb"),
    Path("code/colorfilling_su_1000s.ipynb"),
    Path("code/colorfilling_su_withoutTimeLimit.ipynb"),
]


def first_cell_source(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    return "".join(notebook["cells"][0]["source"])


def first_cell_outputs(path: Path) -> str:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    outputs = notebook["cells"][0].get("outputs", [])
    chunks = []
    for output in outputs:
        chunks.extend(output.get("text", []))
    return "".join(chunks)


def test_notebook_first_cells_do_not_contain_placeholder_question_marks():
    for path in NOTEBOOKS:
        source = first_cell_source(path)
        outputs = first_cell_outputs(path)
        assert "????" not in source, f"{path.name} source still contains placeholder question marks"
        assert "????" not in outputs, f"{path.name} outputs still contain placeholder question marks"


if __name__ == "__main__":
    test_notebook_first_cells_do_not_contain_placeholder_question_marks()
    print("test_notebook_text_integrity.py passed")
