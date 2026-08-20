#!/usr/bin/env python3
"""Frozen analysis for the opened-development relational-object study.

The fitted ridge models are disposable analysis estimators.  This module has no
neural optimizer, representation-training, or checkpoint path.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
from typing import Any, Mapping, Sequence

import numpy as np
from joblib import Parallel, delayed
from sklearn.linear_model import Ridge, RidgeClassifier
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

from relational_objects_v2 import ROOT, load_json, load_jsonl


def _signed_hash(features: Sequence[str], dimensions: int, seed: int) -> np.ndarray:
    out = np.zeros(dimensions, dtype=np.float64)
    prefix = int(seed).to_bytes(8, "little", signed=False)
    for feature in features:
        digest = hashlib.sha256(prefix + feature.encode("utf-8")).digest()
        index = int.from_bytes(digest[:8], "little") % dimensions
        out[index] += 1.0 if (digest[8] & 1) == 0 else -1.0
    return out


def _lexical_features(row: Mapping[str, Any]) -> list[str]:
    cf, hf = str(row["child_form"]).casefold(), str(row["head_form"]).casefold()
    cl, hl = str(row["child_lemma"]).casefold(), str(row["head_lemma"]).casefold()
    return [f"cf={cf}", f"hf={hf}", f"cl={cl}", f"hl={hl}", f"fp={cf}\x1f{hf}", f"lp={cl}\x1f{hl}"]


def _coarse(row: Mapping[str, Any], morph_keys: Sequence[str], vocabulary: Mapping[str, Sequence[str]]) -> np.ndarray:
    def encode(raw: str) -> list[float]:
        parsed={x.split("=",1)[0]:x.split("=",1)[1] for x in raw.split("|") if "=" in x}
        output=[]
        for key in morph_keys:
            observed=parsed.get(key,"NONE"); observed=observed if observed in vocabulary[key] or observed=="NONE" else "OTHER"
            categories=["NONE",*vocabulary[key],"OTHER"]
            output.extend(float(observed==category) for category in categories)
        return output
    values = encode(str(row["child_feats"])) + encode(str(row["head_feats"]))
    values += [float(row["child_is_punct"]), float(row["head_is_punct"])]
    return np.asarray(values, dtype=np.float64)


def make_baselines(examples: Sequence[Mapping[str, Any]], cache: Mapping[str, np.ndarray], config: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    dim, seed = int(config["analysis"]["feature_hash_dimensions"]), int(config["analysis"]["feature_hash_seed"])
    morph = config["matching"]["morph_keys"]; morph_vocabulary=config["matching"]["morph_value_vocabulary"]
    hashes = np.stack([_signed_hash(_lexical_features(row), dim, seed) for row in examples])
    coarse = np.stack([_coarse(row, morph, morph_vocabulary) for row in examples])
    geometry = np.asarray([[row["surface_gap"], row["query_index"], row["causal_key_count"], row["sequence_length"]] for row in examples], dtype=np.float64)
    baseline = np.concatenate([cache["residual_concat"].astype(np.float64), hashes, coarse, geometry], axis=1)
    nuisance = np.concatenate([
        hashes, coarse, geometry, cache["mass"].astype(np.float64),
        cache["query_value_norm"].astype(np.float64), cache["key_value_norm"].astype(np.float64),
        cache["attention_output_norm"].astype(np.float64)[:, None],
    ], axis=1)
    if not np.isfinite(baseline).all() or not np.isfinite(nuisance).all():
        raise RuntimeError("nonfinite deterministic baseline")
    return baseline, nuisance


def _component_weights(components: np.ndarray, multiplicity: Mapping[str, int] | None = None) -> np.ndarray:
    counts = Counter(map(str, components.tolist()))
    return np.asarray([(1.0 / counts[str(component)]) * (1 if multiplicity is None else multiplicity.get(str(component), 0)) for component in components], dtype=np.float64)


def _fit_classifier(X: np.ndarray, y: np.ndarray, weights: np.ndarray, alpha: float, config: Mapping[str, Any]) -> tuple[StandardScaler, RidgeClassifier]:
    keep = weights > 0
    if not keep.any() or set(np.unique(y[keep]).tolist()) != {0, 1}:
        raise RuntimeError("classifier resample lost a class")
    scaler = StandardScaler().fit(X[keep], sample_weight=weights[keep])
    model = RidgeClassifier(
        alpha=float(alpha), solver=str(config["analysis"]["ridge_solver"]),
        tol=float(config["analysis"]["ridge_tolerance"]), max_iter=int(config["analysis"]["ridge_max_iter"]),
        fit_intercept=True, class_weight=None,
    ).fit(scaler.transform(X[keep]), y[keep], sample_weight=weights[keep])
    return scaler, model


def _weighted_auc(y: np.ndarray, score: np.ndarray, weight: np.ndarray) -> float:
    keep = weight > 0
    value = float(roc_auc_score(y[keep], score[keep], sample_weight=weight[keep]))
    if not np.isfinite(value):
        raise RuntimeError("nonfinite AUC")
    return value


def _select_alpha(X: np.ndarray, y: np.ndarray, folds: np.ndarray, components: np.ndarray, multiplicity: Mapping[str, int] | None, config: Mapping[str, Any]) -> tuple[float, list[dict[str, Any]]]:
    rows = []
    for alpha in config["analysis"]["alphas"]:
        scores = []
        for fold in range(int(config["matching"]["folds"])):
            train, valid = folds != fold, folds == fold
            weights = _component_weights(components, multiplicity)
            scaler, model = _fit_classifier(X[train], y[train], weights[train], float(alpha), config)
            prediction = model.decision_function(scaler.transform(X[valid]))
            scores.append(_weighted_auc(y[valid], np.asarray(prediction), weights[valid]))
        rows.append({"alpha": float(alpha), "fold_auc": scores, "mean_auc": float(np.mean(scores))})
    selected = max(rows, key=lambda row: (row["mean_auc"], row["alpha"]))
    return float(selected["alpha"]), rows


def _draw_multiplicity(components: np.ndarray, folds: np.ndarray, seed: int, draw: int, side: str) -> dict[str, int]:
    rng = np.random.default_rng(int(hashlib.sha256(f"{seed}|{draw}|{side}".encode()).hexdigest()[:16], 16))
    output: Counter[str] = Counter()
    for fold in range(5):
        values = sorted(set(map(str, components[folds == fold].tolist())))
        if not values:
            raise RuntimeError("bootstrap fold has no components")
        selected = rng.choice(np.asarray(values, dtype=object), size=len(values), replace=True)
        output.update(map(str, selected.tolist()))
    return dict(output)


def _fit_and_score(X_train: np.ndarray, train: Mapping[str, np.ndarray], X_test: np.ndarray, test: Mapping[str, np.ndarray], train_mult: Mapping[str, int] | None, test_mult: Mapping[str, int] | None, config: Mapping[str, Any]) -> tuple[float, float, list[dict[str, Any]]]:
    alpha, candidates = _select_alpha(X_train, train["label"], train["fold"], train["component"], train_mult, config)
    train_weight = _component_weights(train["component"], train_mult)
    scaler, model = _fit_classifier(X_train, train["label"], train_weight, alpha, config)
    score = np.asarray(model.decision_function(scaler.transform(X_test)), dtype=np.float64)
    auc = _weighted_auc(test["label"], score, _component_weights(test["component"], test_mult))
    return auc, alpha, candidates


def _recovery_draw(draw: int, train: Mapping[str, np.ndarray], test: Mapping[str, np.ndarray], baseline_train: np.ndarray, baseline_test: np.ndarray, add_train: np.ndarray, add_test: np.ndarray, config: Mapping[str, Any]) -> tuple[float, float]:
    train_mult = _draw_multiplicity(train["component"], train["fold"], int(config["seed"]), draw, "fit")
    test_mult = _draw_multiplicity(test["component"], test["fold"], int(config["seed"]), draw, "test")
    base, _, _ = _fit_and_score(baseline_train, train, baseline_test, test, train_mult, test_mult, config)
    augmented, _, _ = _fit_and_score(np.concatenate([baseline_train, add_train], 1), train, np.concatenate([baseline_test, add_test], 1), test, train_mult, test_mult, config)
    return augmented, augmented - base


def _interval(values: Sequence[float], lower: float, method: str) -> dict[str, Any]:
    array = np.asarray(values, dtype=np.float64)
    if array.size != 500 or not np.isfinite(array).all():
        return {"eligible": False, "finite": int(np.isfinite(array).sum()), "required": 500}
    return {"eligible": True, "finite": 500, "lower": float(np.quantile(array, lower, method=method)), "median": float(np.quantile(array, 0.5, method=method)), "upper": float(np.quantile(array, 1-lower, method=method))}


def recovery_direction(train: Mapping[str, Any], test: Mapping[str, Any], path: str, config: Mapping[str, Any]) -> dict[str, Any]:
    add_name = "qk" if path == "qk" else "transport"
    baseline_point, base_alpha, base_candidates = _fit_and_score(train["baseline"], train, test["baseline"], test, None, None, config)
    aug_train = np.concatenate([train["baseline"], train["cache"][add_name].astype(np.float64)], 1)
    aug_test = np.concatenate([test["baseline"], test["cache"][add_name].astype(np.float64)], 1)
    augmented_point, aug_alpha, aug_candidates = _fit_and_score(aug_train, train, aug_test, test, None, None, config)
    draws = Parallel(n_jobs=int(config["analysis"]["parallel_jobs"]), prefer="processes")(
        delayed(_recovery_draw)(draw, train, test, train["baseline"], test["baseline"], train["cache"][add_name].astype(np.float64), test["cache"][add_name].astype(np.float64), config)
        for draw in range(int(config["analysis"]["bootstrap_draws"]))
    )
    auc_interval = _interval([row[0] for row in draws], float(config["analysis"]["recovery_lower_quantile"]), config["analysis"]["quantile_method"])
    gain_interval = _interval([row[1] for row in draws], float(config["analysis"]["recovery_lower_quantile"]), config["analysis"]["quantile_method"])
    gates = {
        "complete": bool(auc_interval["eligible"] and gain_interval["eligible"]),
        "recovery": bool(auc_interval.get("lower", -np.inf) >= float(config["analysis"]["recovery_auc_lower_minimum"])),
        "increment": bool(gain_interval.get("lower", -np.inf) >= float(config["analysis"]["increment_lower_minimum"])),
    }
    gates["all"] = all(gates.values())
    return {
        "fit_source": train["name"], "test_source": test["name"], "path": path,
        "point": {"baseline_auc": baseline_point, "augmented_auc": augmented_point, "gain": augmented_point-baseline_point, "baseline_alpha": base_alpha, "augmented_alpha": aug_alpha},
        "selection": {"baseline": base_candidates, "augmented": aug_candidates},
        "bootstrap": {"augmented_auc": auc_interval, "gain": gain_interval}, "gates": gates,
    }


def _fit_regression(X: np.ndarray, y: np.ndarray, weights: np.ndarray, config: Mapping[str, Any]) -> tuple[StandardScaler, Ridge]:
    keep = weights > 0
    if not keep.any():
        raise RuntimeError("empty regression resample")
    scaler = StandardScaler().fit(X[keep], sample_weight=weights[keep])
    model = Ridge(alpha=float(config["analysis"]["functional_ridge_alpha"]), fit_intercept=True, solver="lsqr", tol=float(config["analysis"]["ridge_tolerance"]), max_iter=int(config["analysis"]["ridge_max_iter"])).fit(scaler.transform(X[keep]), y[keep], sample_weight=weights[keep])
    return scaler, model


def _functional_estimate(rows: Mapping[str, np.ndarray], nuisance: np.ndarray, endpoint: np.ndarray, multiplicity: Mapping[str, int] | None, config: Mapping[str, Any]) -> tuple[float, float]:
    residual = np.empty(len(endpoint), dtype=np.float64)
    weights = _component_weights(rows["component"], multiplicity)
    for fold in range(5):
        train, test = rows["fold"] != fold, rows["fold"] == fold
        if not test.any() or not np.any(weights[test] > 0):
            raise RuntimeError("functional bootstrap lost heldout fold")
        scaler, model = _fit_regression(nuisance[train], endpoint[train], weights[train], config)
        residual[test] = endpoint[test] - model.predict(scaler.transform(nuisance[test]))
    by_component: dict[str, list[float]] = defaultdict(list)
    raw_edges: dict[str, list[float]] = defaultdict(list)
    for edge, nonedge, component in zip(rows["edge_local"], rows["nonedge_local"], rows["pair_component"]):
        by_component[str(component)].append(float(residual[edge] - residual[nonedge]))
        raw_edges[str(component)].append(float(rows["e_abs_local"][edge]))
    numerator = denominator = raw_numerator = 0.0
    for component, values in by_component.items():
        mult = 1 if multiplicity is None else multiplicity.get(component, 0)
        numerator += mult * float(np.mean(values)); raw_numerator += mult * float(np.mean(raw_edges[component])); denominator += mult
    if denominator <= 0:
        raise RuntimeError("empty functional estimand")
    return numerator/denominator, raw_numerator/denominator


def functional_endpoint(source: Mapping[str, Any], orientation: str, endpoint_name: str, config: Mapping[str, Any]) -> dict[str, Any]:
    examples, pairs, cache = source["examples"], source["pairs"], source["cache"]
    bins = np.asarray(config["matching"]["mass_bins"], dtype=np.float64)
    oriented = [pair for pair in pairs if pair["orientation"] == orientation]
    all_head_edges = [pair for pair in oriented if bool(cache["functional_eligible"][int(pair["edge_index"])])]
    selected = []
    nonedge_ineligible=0; mass_bin_mismatch=0
    for pair in all_head_edges:
        edge, nonedge = int(pair["edge_index"]), int(pair["nonedge_index"])
        if not bool(cache["functional_eligible"][nonedge]):
            nonedge_ineligible+=1
            continue
        eb = min(len(bins)-2, max(0, int(np.searchsorted(bins, float(cache["mass"][edge].mean()), side="right")-1)))
        nb = min(len(bins)-2, max(0, int(np.searchsorted(bins, float(cache["mass"][nonedge].mean()), side="right")-1)))
        if eb == nb:
            selected.append(pair)
        else:
            mass_bin_mismatch+=1
    components = sorted({str(pair["component_id"]) for pair in selected})
    coverage = {
        "recovery_edges": len(oriented), "all_head_eligible_edges": len(all_head_edges), "mass_bin_matched_pairs": len(selected), "functional_components": len(components),
        "all_head_rate": len(all_head_edges)/len(oriented) if oriented else 0.0,
        "match_rate_among_all_head_edges": len(selected)/len(all_head_edges) if all_head_edges else 0.0,
        "attrition": {"edge_all_head_ineligible":len(oriented)-len(all_head_edges),"nonedge_all_head_ineligible_after_edge_eligible":nonedge_ineligible,"mean_mass_bin_mismatch_after_both_eligible":mass_bin_mismatch,"retained":len(selected)},
    }
    coverage["gates"] = {
        "all_head": coverage["all_head_rate"] >= float(config["analysis"]["all_head_eligibility_minimum"]),
        "matched": coverage["match_rate_among_all_head_edges"] >= float(config["analysis"]["functional_match_minimum"]),
        "components": coverage["functional_components"] >= int(config["matching"]["minimum_functional_components_per_orientation"]),
    }
    if not all(coverage["gates"].values()):
        return {"eligible": False, "source": source["name"], "orientation": orientation, "endpoint": endpoint_name, "coverage": coverage, "reason": "coverage_gate_failed"}
    selected_indices = sorted({int(pair[k]) for pair in selected for k in ("edge_index", "nonedge_index")})
    global_to_local = {value:index for index,value in enumerate(selected_indices)}
    subset_examples = [examples[index] for index in selected_indices]
    rows = {
        "component": np.asarray([row["component_id"] for row in subset_examples]),
        "fold": np.asarray([row["fold"] for row in subset_examples], dtype=np.int64),
        "edge_local": np.asarray([global_to_local[int(pair["edge_index"])] for pair in selected], dtype=np.int64),
        "nonedge_local": np.asarray([global_to_local[int(pair["nonedge_index"])] for pair in selected], dtype=np.int64),
        "pair_component": np.asarray([pair["component_id"] for pair in selected]),
        "e_abs_local": cache["e_abs"][selected_indices].astype(np.float64),
    }
    endpoint = cache[endpoint_name][selected_indices].astype(np.float64)
    nuisance = source["nuisance"][selected_indices]
    point, raw_point = _functional_estimate(rows, nuisance, endpoint, None, config)
    def one(draw: int) -> tuple[float,float]:
        mult = _draw_multiplicity(rows["component"], rows["fold"], int(config["seed"])+991, draw, f"functional:{source['name']}:{orientation}")
        return _functional_estimate(rows, nuisance, endpoint, mult, config)
    draws = Parallel(n_jobs=int(config["analysis"]["parallel_jobs"]), prefer="processes")(delayed(one)(draw) for draw in range(500))
    effect = _interval([row[0] for row in draws], float(config["analysis"]["functional_lower_quantile"]), config["analysis"]["quantile_method"])
    raw = _interval([row[1] for row in draws], float(config["analysis"]["functional_lower_quantile"]), config["analysis"]["quantile_method"])
    gates = {"effect_positive": effect.get("lower", -np.inf) > 0, "raw_edge_abs": raw.get("lower", -np.inf) >= float(config["analysis"]["functional_edge_abs_lower_minimum"]), "complete": bool(effect["eligible"] and raw["eligible"])}
    gates["all"] = all(gates.values())
    return {"eligible": True, "source": source["name"], "orientation": orientation, "endpoint": endpoint_name, "coverage": coverage, "point": {"adjusted_edge_minus_nonedge": point, "raw_edge_e_abs": raw_point}, "bootstrap": {"adjusted_effect": effect, "raw_edge_e_abs": raw}, "gates": gates}


def _descriptive_transfer(train: Mapping[str, Any], test: Mapping[str, Any], feature: str, config: Mapping[str, Any]) -> dict[str, Any]:
    Xtr, Xte = train["cache"][feature].astype(np.float64), test["cache"][feature].astype(np.float64)
    auc, alpha, _ = _fit_and_score(Xtr, train, Xte, test, None, None, config)
    return {"feature": feature, "fit_source": train["name"], "test_source": test["name"], "auc": auc, "alpha": alpha, "role": "DESCRIPTIVE_NON_GATING"}


def _descriptive_relation_transfer(train: Mapping[str, Any], test: Mapping[str, Any], feature: str, classes: Sequence[str], config: Mapping[str, Any]) -> dict[str, Any]:
    if len(classes)<2:
        return {"feature":feature,"eligible":False,"reason":"fewer_than_two_supported_classes","classes":list(classes),"role":"DESCRIPTIVE_NON_GATING"}
    train_indices=np.asarray([i for i,row in enumerate(train["examples"]) if row["label"]==1 and row["relation"] in classes],dtype=np.int64)
    test_indices=np.asarray([i for i,row in enumerate(test["examples"]) if row["label"]==1 and row["relation"] in classes],dtype=np.int64)
    ytrain=np.asarray([train["examples"][i]["relation"] for i in train_indices]); ytest=np.asarray([test["examples"][i]["relation"] for i in test_indices])
    if set(ytrain.tolist())!=set(classes) or set(ytest.tolist())!=set(classes):
        return {"feature":feature,"eligible":False,"reason":"missing_class","classes":list(classes),"role":"DESCRIPTIVE_NON_GATING"}
    Xtrain=train["cache"][feature][train_indices].astype(np.float64); Xtest=test["cache"][feature][test_indices].astype(np.float64)
    folds=train["fold"][train_indices]; components=train["component"][train_indices]; weights=_component_weights(components)
    candidates=[]
    for alpha in config["analysis"]["alphas"]:
        scores=[]; valid=True
        for fold in range(5):
            fit,validation=folds!=fold,folds==fold
            if set(ytrain[fit].tolist())!=set(classes) or set(ytrain[validation].tolist())!=set(classes): valid=False; break
            scaler=StandardScaler().fit(Xtrain[fit],sample_weight=weights[fit])
            model=RidgeClassifier(alpha=float(alpha),solver=str(config["analysis"]["ridge_solver"]),tol=float(config["analysis"]["ridge_tolerance"]),max_iter=int(config["analysis"]["ridge_max_iter"]),fit_intercept=True,class_weight=None).fit(scaler.transform(Xtrain[fit]),ytrain[fit],sample_weight=weights[fit])
            prediction=model.predict(scaler.transform(Xtrain[validation]))
            scores.append(float(f1_score(ytrain[validation],prediction,labels=list(classes),average="macro",sample_weight=weights[validation],zero_division=0)))
        candidates.append({"alpha":float(alpha),"valid":valid,"fold_macro_f1":scores,"mean_macro_f1":float(np.mean(scores)) if valid else None})
    valid=[row for row in candidates if row["valid"]]
    if not valid: return {"feature":feature,"eligible":False,"reason":"class_missing_in_fold","classes":list(classes),"candidates":candidates,"role":"DESCRIPTIVE_NON_GATING"}
    selected=max(valid,key=lambda row:(row["mean_macro_f1"],row["alpha"]))
    scaler=StandardScaler().fit(Xtrain,sample_weight=weights)
    model=RidgeClassifier(alpha=selected["alpha"],solver=str(config["analysis"]["ridge_solver"]),tol=float(config["analysis"]["ridge_tolerance"]),max_iter=int(config["analysis"]["ridge_max_iter"]),fit_intercept=True,class_weight=None).fit(scaler.transform(Xtrain),ytrain,sample_weight=weights)
    test_weights=_component_weights(test["component"][test_indices])
    macro=float(f1_score(ytest,model.predict(scaler.transform(Xtest)),labels=list(classes),average="macro",sample_weight=test_weights,zero_division=0))
    return {"feature":feature,"eligible":True,"classes":list(classes),"selected_alpha":selected["alpha"],"macro_f1":macro,"candidates":candidates,"role":"DESCRIPTIVE_NON_GATING"}


def _load_source(name: str, config: Mapping[str, Any], cache_root: Any) -> dict[str, Any]:
    root = ROOT / config["paths"]["prepared_root"] / name
    examples, pairs = load_jsonl(root/"examples.jsonl"), load_jsonl(root/"pairs.jsonl")
    with np.load(cache_root/f"{name}.features.npz", allow_pickle=False) as z:
        cache = {key:np.array(z[key],copy=True) for key in z.files}
    n = len(examples)
    shapes = {"residual_concat":(n,1536),"residual_difference":(n,768),"qk":(n,12),"mass":(n,12),"transport":(n,768),"head_output":(n,768),"query_value_norm":(n,12),"key_value_norm":(n,12),"attention_output_norm":(n,),"block_input_rms":(n,),"e_local":(n,),"e_abs":(n,),"e_abs64":(n,),"functional_eligible":(n,),"example_index":(n,),"label":(n,),"fold":(n,)}
    for key, shape in shapes.items():
        if key not in cache or cache[key].shape != shape or (key not in {"functional_eligible","e_local","e_abs","e_abs64"} and not np.isfinite(cache[key]).all()):
            raise RuntimeError(f"cache contract failure {name}:{key}")
    eligible=cache["functional_eligible"].astype(bool)
    for key in ("e_local","e_abs","e_abs64"):
        if not np.isfinite(cache[key][eligible]).all() or not np.isnan(cache[key][~eligible]).all():
            raise RuntimeError(f"cache functional-missingness contract failure {name}:{key}")
    if not np.array_equal(cache["example_index"], np.arange(n)) or not np.array_equal(cache["label"], np.asarray([r["label"] for r in examples])) or not np.array_equal(cache["fold"], np.asarray([r["fold"] for r in examples])):
        raise RuntimeError(f"cache row lineage failure: {name}")
    baseline,nuisance=make_baselines(examples,cache,config)
    return {"name":name,"examples":examples,"pairs":pairs,"cache":cache,"baseline":baseline,"nuisance":nuisance,"label":cache["label"].astype(np.int64),"fold":cache["fold"].astype(np.int64),"component":np.asarray([r["component_id"] for r in examples])}


def analyze(config: Mapping[str, Any], cache_root: Any) -> dict[str, Any]:
    names=sorted(config["sources"])
    sources={name:_load_source(name,config,cache_root) for name in names}
    directions=[]
    for fit,test in ((names[0],names[1]),(names[1],names[0])):
        for path in ("qk","transport"):
            directions.append(recovery_direction(sources[fit],sources[test],path,config))
    functional=[]
    for source in names:
        for orientation in ("later_query_is_head","later_query_is_child"):
            for endpoint in ("e_local","e_abs"):
                functional.append(functional_endpoint(sources[source],orientation,endpoint,config))
    paths={}
    for path in ("qk","transport"):
        relevant=[row for row in directions if row["path"]==path]
        paths[path]={"directions":relevant,"bidirectional_pass":all(row["gates"]["all"] for row in relevant)}
    functional_pass=all(row.get("eligible") and row.get("gates",{}).get("all") for row in functional)
    nominated=[path for path,row in paths.items() if row["bidirectional_pass"] and functional_pass]
    decision="DEVELOPMENT_NOMINATION_FOR_FRESH_PREREGISTRATION" if nominated else "RELATIONAL_OBJECTS_NOT_NOMINATED_NO_LEARNED_MODEL"
    descriptive=[]
    relation_docs={}
    for name in names:
        grouped:dict[str,set[str]]=defaultdict(set)
        for row in sources[name]["examples"]:
            if row["label"]==1 and row["relation"] is not None: grouped[str(row["relation"])].add(str(row["document_id"]))
        relation_docs[name]={key:len(value) for key,value in grouped.items()}
    relation_classes=sorted(set.intersection(*[{key for key,value in relation_docs[name].items() if value>=20} for name in names]))
    relation_transfer=[]
    for fit,test in ((names[0],names[1]),(names[1],names[0])):
        for feature in ("residual_concat","residual_difference","qk","mass","transport","head_output"):
            descriptive.append(_descriptive_transfer(sources[fit],sources[test],feature,config))
            relation_transfer.append({"fit_source":fit,"test_source":test,**_descriptive_relation_transfer(sources[fit],sources[test],feature,relation_classes,config)})
    return {
        "schema_version":"relational_objects_v2_result_v1","scope":"OPENED_DEVELOPMENT_EXPLORATORY",
        "decision":decision,"nominated_paths":nominated,"recovery_paths":paths,"functional":functional,"functional_global_pass":functional_pass,
        "descriptive_transfer":descriptive,"descriptive_relation_transfer":{"document_support":relation_docs,"classes":relation_classes,"results":relation_transfer},"neural_training_run":False,"representation_training_run":False,"fresh_scientific_corpus_accessed":False,
        "permitted_claim":"Among opened-development matched pairs, report object recovery and local attention-block specificity only; no confirmatory, modularity, or downstream-causal claim is authorized."
    }
