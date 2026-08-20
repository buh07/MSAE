from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_relational_objects_v2 import morph_signature
from scout_relational_objects_v3 import _support, canonical_cap_components


def test_complete_morphology_values_remain_distinct() -> None:
    vocabulary = {"Case": ["Nom", "Acc"], "Number": ["Sing"]}
    assert morph_signature("Case=Nom|Number=Sing", ["Case", "Number"], vocabulary) != morph_signature(
        "Case=Acc|Number=Sing", ["Case", "Number"], vocabulary
    )
    assert morph_signature("Case=Dat", ["Case", "Number"], vocabulary) == (
        "Case=OTHER",
        "Number=NONE",
    )


def test_support_counts_both_pair_directions_and_unique_documents() -> None:
    component = {
        "component_id": "c0",
        "documents": ["d0", "d1"],
        "fold": 0,
        "left_positive_pairs": [{"edge": {"orientation": "later_query_is_head"}}],
        "right_positive_pairs": [{"edge": {"orientation": "later_query_is_child"}}],
    }
    observed = _support("SOURCE", [component], {"retained": 2})
    assert observed["components"] == 1
    assert observed["documents"] == 2
    assert observed["pairs"] == 2
    assert observed["orientations"] == {
        "later_query_is_child": 1,
        "later_query_is_head": 1,
    }


def test_scout_has_no_model_or_forward_surface() -> None:
    path = ROOT / "scripts" / "scout_relational_objects_v3.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert "AutoModel" not in imported
    text = path.read_text(encoding="utf-8")
    assert ".backward(" not in text
    assert "torch.optim" not in text
    assert "model.forward" not in text


def test_canonical_cap_preserves_both_directions_before_stable_trim() -> None:
    def pair(name: str, orientation: str) -> dict:
        return {"pair_id": name, "edge": {"orientation": orientation}}

    components = [
        {
            "component_id": "c0",
            "documents": ["d0", "d1"],
            "fold": 4,
            "pair_count": 4,
            "left_positive_pairs": [pair("b", "later_query_is_head"), pair("d", "later_query_is_head")],
            "right_positive_pairs": [pair("a", "later_query_is_child"), pair("c", "later_query_is_child")],
        },
        {
            "component_id": "c1",
            "documents": ["d2", "d3"],
            "fold": 4,
            "pair_count": 2,
            "left_positive_pairs": [pair("e", "later_query_is_head")],
            "right_positive_pairs": [pair("f", "later_query_is_child")],
        },
    ]
    capped = canonical_cap_components(components, maximum_components=1, target_pairs=3)
    assert len(capped) == 1
    assert capped[0]["fold"] == 0
    assert capped[0]["pair_count"] == 3
    assert [row["pair_id"] for row in capped[0]["left_positive_pairs"]] == ["b"]
    assert [row["pair_id"] for row in capped[0]["right_positive_pairs"]] == ["a", "c"]


def test_scout_configuration_is_permanently_development_only() -> None:
    import json

    config = json.loads((ROOT / "configs" / "relational_objects_v3" / "scout.json").read_text())
    assert len(config["source_selection_order"]) == 8
    assert all(source["role"] == "OPENED_DEVELOPMENT_ONLY" for source in config["sources"].values())
    assert not any(config["permissions"].values())
    assert config["matching"]["minimum_components"] == 100
    assert config["matching"]["minimum_pairs"] == 500
