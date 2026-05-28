# Pilot Implementation Notes (16GB VRAM Friendly)

This adds a runnable implementation of the Paper 1 de-risking experiment:
- Script: `MSAE/scripts/raw_activation_separability_pilot.py`
- Convenience runner: `MSAE/scripts/run_small_model_pilot.sh`

## What it does
1. Loads a causal LM and tokenizer (HF `AutoModelForCausalLM`).
2. Streams text from a dataset (`wikitext` by default).
3. Collects token-level hidden activations from a chosen layer.
4. Trains linear probes for:
   - Position prediction
   - Token-identity prediction (top-K frequent tokens)
5. Builds probe-derived subspaces (`S_pos`, `S_tok`) by SVD on probe weights.
6. Evaluates projected representations:
   - `Proj_{S_pos}(x)`, `Proj_{S_pos^perp}(x)`
   - `Proj_{S_tok}(x)`, `Proj_{S_tok^perp}(x)`
7. Computes principal-angle and cross-projection overlap diagnostics.
8. Applies the threshold checks from `MSAE_revised.md` §1.5B.

Outputs:
- `raw_sep_summary.json`
- `raw_sep_rank_table.csv`

## Quick start
```bash
bash MSAE/scripts/run_small_model_pilot.sh
```

## Suggested 16GB models for pilot
- `EleutherAI/pythia-14m-deduped` (very safe first run)
- `EleutherAI/pythia-70m-deduped` (still comfortable)
- `gpt2` / `distilgpt2` (if you want extremely fast smoke tests)

For Pythia-160M on 16GB, use conservative settings:
- `context_length <= 128`
- `batch_size <= 4`
- `max_tokens_collect` modest for first run (e.g., 40k-80k)

## Practical tuning knobs when VRAM is tight
- Lower `--batch_size`.
- Lower `--context_length`.
- Use smaller model.
- Keep `--dtype auto` (FP16 on CUDA).
- Reduce `--max_tokens_collect` for initial debug runs.

## Example custom run
```bash
MODEL=EleutherAI/pythia-70m-deduped \
MAX_TEXT_SAMPLES=3000 \
MAX_TOKENS=80000 \
BATCH_SIZE=4 \
LAYER_INDEX=4 \
bash MSAE/scripts/run_small_model_pilot.sh
```

