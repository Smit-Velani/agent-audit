import json
import os

GOLDEN_SET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "golden_set.jsonl")


def load_golden_set():
    tasks = []
    with open(GOLDEN_SET_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                tasks.append(json.loads(line))
    return tasks


def test_golden_set_has_correct_count():
    tasks = load_golden_set()
    assert len(tasks) == 29


def test_golden_set_has_all_categories():
    tasks = load_golden_set()
    categories = {t["category"] for t in tasks}
    assert "happy_path" in categories
    assert "edge_case" in categories
    assert "adversarial" in categories


def test_golden_set_all_tasks_have_required_fields():
    tasks = load_golden_set()
    for t in tasks:
        assert "id" in t, f"Task missing id: {t}"
        assert "question" in t
        assert "expected" in t
        assert "category" in t


def test_golden_set_adversarial_count():
    tasks = load_golden_set()
    adversarial = [t for t in tasks if t["category"] == "adversarial"]
    assert len(adversarial) >= 5