"""Static audit for Module 4 Checkpoint 05: markers and coverage configuration."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests"
PYTEST_INI = ROOT / "pytest.ini"
REQUIRED_MARKERS = {"web", "buttons", "analysis", "db", "integration"}


def _marker_from_expr(expr: ast.AST) -> set[str]:
    """Return marker names from ``pytest.mark.<name>`` expressions."""
    if isinstance(expr, ast.Attribute):
        value = expr.value
        if (
            isinstance(value, ast.Attribute)
            and value.attr == "mark"
            and isinstance(value.value, ast.Name)
            and value.value.id == "pytest"
        ):
            return {expr.attr}
    return set()


def marker_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    found: set[str] = set()
    for decorator in node.decorator_list:
        found |= _marker_from_expr(decorator)
    return found


def module_marker_names(tree: ast.Module) -> set[str]:
    """Recognize pytest's supported module-level ``pytestmark`` declaration."""
    found: set[str] = set()
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "pytestmark" for target in targets):
            continue
        value = node.value
        if isinstance(value, (ast.List, ast.Tuple)):
            for item in value.elts:
                found |= _marker_from_expr(item)
        else:
            found |= _marker_from_expr(value)
    return found


def main() -> None:
    failures: list[str] = []
    ini = PYTEST_INI.read_text(encoding="utf-8")

    checks = {
        "coverage source configured": "--cov=module_4/src" in ini,
        "term-missing report configured": "--cov-report=term-missing" in ini,
        "100 percent gate configured": "--cov-fail-under=100" in ini,
    }
    for marker in REQUIRED_MARKERS:
        checks[f"marker registered: {marker}"] = f"{marker}:" in ini

    test_functions = 0
    unmarked: list[str] = []
    unknown_markers: list[str] = []
    for path in sorted(TESTS.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        module_markers = module_marker_names(tree)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                test_functions += 1
                markers = marker_names(node) | module_markers
                if not markers:
                    unmarked.append(f"{path.name}::{node.name}")
                bad = markers - REQUIRED_MARKERS
                unknown_markers.extend(f"{path.name}::{node.name} -> {m}" for m in bad)

    checks["test suite contains tests"] = test_functions > 0
    checks["no unmarked tests"] = not unmarked
    checks["no unknown test markers"] = not unknown_markers

    print("CHECKPOINT 05 STATIC AUDIT")
    for label, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}: {label}")
        if not ok:
            failures.append(label)

    if unmarked:
        print("  Unmarked tests:")
        for item in unmarked:
            print(f"    - {item}")
    if unknown_markers:
        print("  Unknown markers:")
        for item in unknown_markers:
            print(f"    - {item}")

    if failures:
        raise SystemExit("CHECKPOINT 05 STATIC AUDIT: FAIL")
    print(f"CHECKPOINT 05 STATIC AUDIT: PASS ({test_functions} tests inspected)")


if __name__ == "__main__":
    main()
