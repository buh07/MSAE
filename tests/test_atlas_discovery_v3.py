from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from atlas_discovery_v3 import (
    Sentence,
    Token,
    basis_overlap,
    bootstrap_component_multiplicities,
    build_joint_cross_family_rows,
    build_projector,
    label_blind_cap,
    maximum_cardinality_document_matching,
    parse_conllu,
    pooled_document_row_weights,
    position_factorial,
    raw_coordinate_weights,
    resolve_source_inputs,
    select_sham_heads,
    stable_fold,
    terminal_outcome,
)


def test_resolve_source_inputs_rejects_mixed_parent_before_open(tmp_path: Path) -> None:
    ewt = tmp_path / "ewt.conllu"
    gum = tmp_path / "gum.conllu"
    ewt.write_text("# harmless\n", encoding="utf-8")
    gum.write_text("# harmless\n", encoding="utf-8")
    config = {
        "repository_root": str(tmp_path),
        "sources": {
            "EWT": {"path": "ewt.conllu", "sha256": "0" * 64},
            "GUM": {"path": "mixed/discovery.records.jsonl", "sha256": "0" * 64},
        },
    }
    with pytest.raises(RuntimeError, match="not exact allowlisted source"):
        resolve_source_inputs(config, verify_digests=False)


def test_parse_conllu_preserves_documents_heads_and_paragraphs(tmp_path: Path) -> None:
    path = tmp_path / "tiny.conllu"
    path.write_text(
        "\n".join(
            [
                "# newdoc id = d1",
                "# newpar id = p1",
                "# sent_id = d1-1",
                "1\tCats\tcat\tNOUN\t_\tNumber=Plur\t2\tnsubj\t_\t_",
                "2\trun\trun\tVERB\t_\tNumber=Plur\t0\troot\t_\t_",
                "",
                "# sent_id = d1-2",
                "1\tFast\tfast\tADV\t_\t_\t2\tadvmod\t_\t_",
                "2\tnow\tnow\tADV\t_\t_\t0\troot\t_\t_",
                "",
            ]
        ),
        encoding="utf-8",
    )
    rows = parse_conllu(path, "EWT")
    assert [row.sent_id for row in rows] == ["d1-1", "d1-2"]
    assert rows[0].document_id == "d1"
    assert rows[0].paragraph_id == "p1"
    assert rows[0].tokens[0].head == 2
    assert rows[0].tokens[0].feats == {"Number": "Plur"}


def test_parse_conllu_rejects_sentence_before_document(tmp_path: Path) -> None:
    path = tmp_path / "bad.conllu"
    path.write_text(
        "# sent_id = x\n1\tx\tx\tX\t_\t_\t0\troot\t_\t_\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="before newdoc"):
        parse_conllu(path, "EWT")


def test_parse_conllu_counts_nonrepresentation_rows(tmp_path: Path) -> None:
    path = tmp_path / "artifacts.conllu"
    path.write_text(
        "\n".join(
            [
                "# newdoc id = d1",
                "# sent_id = d1-1",
                "1-2\tcan't\t_\t_\t_\t_\t_\t_\t_\t_",
                "1\tca\tcan\tAUX\t_\t_\t2\taux\t_\t_",
                "2\tn't\tnot\tPART\t_\t_\t0\troot\t_\t_",
                "2.1\tghost\tghost\tX\t_\t_\t_\t_\t_\t_",
                "",
            ]
        ),
        encoding="utf-8",
    )
    exclusions: dict[str, int] = {}
    rows = parse_conllu(path, "EWT", exclusion_counts=exclusions)
    assert len(rows) == 1
    assert exclusions == {"multiword_token_rows": 1, "empty_node_rows": 1}


def test_label_blind_cap_does_not_depend_on_labels() -> None:
    rows = [{"row_id": f"r{i}", "label": str(i % 3)} for i in range(20)]
    relabeled = [{**row, "label": "changed"} for row in rows]
    left = [x["row_id"] for x in label_blind_cap(rows, 7, seed=11)]
    right = [x["row_id"] for x in label_blind_cap(relabeled, 7, seed=11)]
    assert left == right
    assert len(left) == 7


def test_stable_fold_is_deterministic_and_bounded() -> None:
    assert stable_fold("EWT", "doc", seed=20260803, folds=5) == stable_fold(
        "EWT", "doc", seed=20260803, folds=5
    )
    assert 0 <= stable_fold("GUM", "doc", seed=20260803, folds=5) < 5


def test_bootstrap_components_is_deterministic_and_counts_slots() -> None:
    first = bootstrap_component_multiplicities(
        ["c", "a", "b"], direction="EWT_to_GUM", endpoint="token", draw=4, seed=7
    )
    second = bootstrap_component_multiplicities(
        ["c", "a", "b"], direction="EWT_to_GUM", endpoint="token", draw=4, seed=7
    )
    assert first == second
    assert sum(first.values()) == 3


def test_maximum_matching_is_role_disjoint_and_maximal() -> None:
    candidates = [
        {"candidate_id": "a", "left_document": "d1", "right_document": "d2"},
        {"candidate_id": "b", "left_document": "d2", "right_document": "d3"},
        {"candidate_id": "c", "left_document": "d3", "right_document": "d4"},
    ]
    selected, report = maximum_cardinality_document_matching(candidates)
    documents = [
        document
        for row in selected
        for document in (row["left_document"], row["right_document"])
    ]
    assert len(selected) == 2
    assert len(documents) == len(set(documents))
    assert report["maximum_cardinality"] == 2
    assert report["achieved_cardinality"] == 2


def test_pooled_document_weights_share_multipliers_across_endpoints() -> None:
    rows = [
        {"document_group": "d1"},
        {"document_group": "d1", "donor_document_group": "d2"},
        {"document_group": "d2"},
    ]
    weights = pooled_document_row_weights(rows, {"d1": 2, "d2": 3})
    assert weights.tolist() == [2.0, 6.0, 3.0]


def test_joint_cross_family_rows_balance_exact_strata() -> None:
    metadata = {
        "start_distance": "4-7",
        "upos_coarse": "NOMINAL",
        "capitalization": "title",
        "word_length": "5-7",
        "sentence_length": "9-16",
    }
    pairs = [
        {
            "pair_id": "r1",
            "construct": "relative_gap",
            "document_group": "EWT:d1",
            "fold": 0,
            "target_metadata": metadata,
            "rows": {"bare": {"post": "a"}, "relative_gap": {"post": "b"}},
        },
        {
            "pair_id": "c1",
            "construct": "context_factorial",
            "document_group": "EWT:d2",
            "donor_document_group": "EWT:d3",
            "fold": 0,
            "target_metadata": metadata,
            "rows": {"separator_only": "c", "unrelated_prefix": "d", "true_prefix": "e"},
        },
        {
            "pair_id": "p1",
            "construct": "proper_noun_substitution",
            "document_group": "EWT:d4",
            "donor_document_group": "EWT:d5",
            "fold": 0,
            "target_metadata": metadata,
            "rows": {
                "source": {"changed": "f", "control": "g"},
                "target": {"changed": "h", "control": "i"},
            },
        },
    ]
    rows, report = build_joint_cross_family_rows(pairs, source="EWT", seed=20260803)
    assert report["retained_by_class"] == {
        "proper_noun_substitution": 1,
        "relative_gap": 1,
        "true_context": 1,
        "unrelated_context": 1,
    }
    assert len(rows) == 4
    excluded, excluded_report = build_joint_cross_family_rows(
        pairs, source="EWT", seed=20260803, allowed_joint_cells={"not|a|real|cell"}
    )
    assert excluded == []
    assert excluded_report["raw_candidate_by_class"]["relative_gap"] == 1
    assert excluded_report["candidate_by_class"]["relative_gap"] == 0


def test_position_factorial_matches_target_position_ids() -> None:
    variants = position_factorial(
        target_ids=[10, 11, 12],
        true_prefix_ids=[20, 21],
        unrelated_prefix_ids=[30, 31],
        separator_id=0,
        shift=16,
        pivot_token_index=1,
    )
    assert variants["bare"]["input_ids"] == [10, 11, 12]
    assert variants["uniform_shift"]["position_ids"] == [16, 17, 18]
    assert variants["prefix_position_only"]["position_ids"] == [3, 4, 5]
    assert variants["separator_only"]["position_ids"] == [0, 3, 4, 5]
    assert variants["true_prefix"]["position_ids"][-3:] == [3, 4, 5]
    assert variants["unrelated_prefix"]["position_ids"][-3:] == [3, 4, 5]
    assert variants["relative_gap"]["position_ids"] == [0, 17, 18]


def _sentence_for_sham() -> Sentence:
    # Child token 5 -> true head 2: left/far/NOMINAL; token 1 is an exact sham.
    return Sentence(
        source="EWT",
        document_id="d",
        paragraph_id=None,
        sent_id="s",
        text=None,
        tokens=(
            Token(1, "A", "a", "NOUN", {}, 0, "root"),
            Token(2, "B", "b", "NOUN", {}, 0, "root"),
            Token(3, "C", "c", "ADV", {}, 0, "root"),
            Token(4, "D", "d", "VERB", {}, 0, "root"),
            Token(5, "E", "e", "ADV", {}, 2, "obl"),
        ),
    )


def test_sham_head_matching_uses_exact_stratum_and_never_true_head() -> None:
    matches = select_sham_heads(
        _sentence_for_sham(),
        aligned_token_ids={1, 2, 3, 4, 5},
        coarse_upos={"NOUN": "NOMINAL", "VERB": "VERBAL", "ADV": "MODIFIER"},
        seed=20260803,
    )
    assert matches
    assert all(row["head_token_id"] != row["sham_token_id"] for row in matches)
    assert len({row["sham_token_id"] for row in matches}) == len(matches)


def test_raw_coordinate_weight_conversion() -> None:
    wz = np.asarray([[2.0, 6.0], [4.0, 10.0]])
    scale = np.asarray([2.0, 4.0])
    raw = raw_coordinate_weights(wz, scale)
    np.testing.assert_allclose(raw, [[-0.5, -0.5], [0.5, 0.5]])


def test_projector_is_symmetric_idempotent_and_additive() -> None:
    blocks = [np.asarray([[1.0, 0.0, 0.0]]), np.asarray([[0.0, 1.0, 0.0]])]
    projector, meta = build_projector(blocks, rank=2, singular_floor=1e-8)
    np.testing.assert_allclose(projector, projector.T, atol=1e-12)
    np.testing.assert_allclose(projector @ projector, projector, atol=1e-12)
    x = np.asarray([[1.0, 2.0, 3.0]])
    np.testing.assert_allclose(x @ projector + x @ (np.eye(3) - projector), x)
    assert meta["rank"] == 2


def test_basis_overlap_identity_and_orthogonal() -> None:
    a = np.asarray([[1.0, 0.0], [0.0, 1.0]]).T
    b = np.asarray([[1.0, 0.0], [0.0, 1.0]]).T
    c = np.asarray([[0.0], [0.0], [1.0]])
    # Embed a/b into the same three-dimensional feature space.
    a3 = np.vstack([a, np.zeros((1, 2))])
    b3 = np.vstack([b, np.zeros((1, 2))])
    assert basis_overlap(a3, b3) == pytest.approx(1.0)
    assert basis_overlap(a3, c) == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("statuses", "expected"),
    [
        ({"a": "ineligible", "b": "eligible_not_passed", "c": "eligible_not_passed"}, "technically_ineligible"),
        ({"a": "eligible_not_passed", "b": "eligible_not_passed", "c": "eligible_not_passed"}, "no_decomposition_nominated"),
        ({"a": "passed", "b": "eligible_not_passed", "c": "eligible_not_passed"}, "nominate_a"),
        ({"a": "passed", "b": "passed", "c": "eligible_not_passed"}, "multiple_discovery_candidates"),
    ],
)
def test_terminal_outcome_is_total(statuses: dict[str, str], expected: str) -> None:
    assert terminal_outcome(statuses, technical_failure=False) == expected
    assert terminal_outcome(statuses, technical_failure=True) == "technically_ineligible"
