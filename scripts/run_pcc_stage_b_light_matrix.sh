#!/usr/bin/env bash
set -euo pipefail

ROOT="${REPO_ROOT}"
TS="$(date +%Y%m%d_%H%M%S)"
RUN_ROOT="$ROOT/pilot_runs/${TS}_pcc_stage_b_light_controls"
LOG_DIR="$RUN_ROOT/logs"
OUT_DIR="$RUN_ROOT/outputs"
CACHE_DIR="$RUN_ROOT/cache"
mkdir -p "$LOG_DIR" "$OUT_DIR" "$CACHE_DIR"

MANIFEST="$RUN_ROOT/run_manifest.tsv"
SESSIONS="$RUN_ROOT/tmux_sessions.txt"
: > "$SESSIONS"
printf 'job_id\tgpu\tseed\tlambda\tcheckpoint_path\toutput_dir\tlog_path\tsession_name\n' > "$MANIFEST"

GIT_HASH="$(cd "$ROOT" && git rev-parse HEAD 2>/dev/null || true)"

launch_job() {
  local job_id="$1"
  local gpu="$2"
  local seed="$3"
  local lam="$4"
  local ckpt="$5"
  local outdir="$OUT_DIR/$job_id"
  local logfile="$LOG_DIR/${job_id}.log"
  local job_cache="$CACHE_DIR/$job_id"
  local session="pcc-bl-${job_id}-${TS}"
  mkdir -p "$outdir" "$job_cache"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$job_id" "$gpu" "$seed" "$lam" "$ckpt" "$outdir" "$logfile" "$session" >> "$MANIFEST"
  echo "$session" >> "$SESSIONS"
  tmux new-session -d -s "$session" bash -lc "
    set -euo pipefail
    export PYTHONUNBUFFERED=1
    export HF_HOME='/jumbo/lisp/f004ndc/.cache/huggingface'
    export HF_DATASETS_CACHE='/jumbo/lisp/f004ndc/.cache/huggingface/datasets'
    export XDG_CACHE_HOME='/jumbo/lisp/f004ndc/.cache'
    export TMPDIR='/jumbo/lisp/f004ndc/tmp'
    cd '$ROOT'
    echo [start] job=$job_id gpu=$gpu seed=$seed lambda=$lam layer=3 model=EleutherAI/pythia-160m-deduped checkpoint=$ckpt
    CUDA_VISIBLE_DEVICES=$gpu python -u '$ROOT/scripts/pcc_stage_b_light_controls.py' \
      --checkpoint_path '$ckpt' \
      --model_name 'EleutherAI/pythia-160m-deduped' \
      --layer_index 3 \
      --seed '$seed' \
      --device cuda \
      --dtype auto \
      --output_dir '$outdir' \
      --git_commit_hash '$GIT_HASH' \
      --context_length 192 \
      --model_batch_size 12 \
      --probe_backend torch \
      --probe_torch_max_steps 1200 \
      --probe_torch_max_steps_semantic 2200 \
      --probe_torch_batch_size 8192 \
      --probe_torch_lr 0.02 \
      --probe_torch_scheduler cosine \
      --probe_torch_eval_every 50 \
      --probe_torch_patience 300 \
      --probe_torch_patience_semantic 500 \
      --probe_torch_min_steps 200 \
      --probe_torch_min_steps_semantic 300 \
      --probe_torch_lr_position_raw_highdim 0.01 \
      --probe_torch_lr_position_raw_highdim_threshold 768 \
      --min_examples_per_class 20 \
      --max_train_sentences_ud 4000 \
      --max_eval_sentences_ud 1000 \
      --max_train_sentences_wnut 3394 \
      --max_eval_sentences_wnut 1009 \
      --max_train_sentences_fewnerd 12000 \
      --max_eval_sentences_fewnerd 3000 \
      --max_train_sentences_wikineural 12000 \
      --max_eval_sentences_wikineural 3000 \
      --cache_dir '$job_cache'
    echo [done] job=$job_id
  " > "$logfile" 2>&1
}

launch_job "pcc_bl_g4_L3_s42_inc1e2" 4 42 1e-2 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/checkpoints/final_step249244_tok1000000016.pt"
launch_job "pcc_bl_g5_L3_s43_inc1e2" 5 43 1e-2 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/checkpoints/final_step249244_tok1000000016.pt"
launch_job "pcc_bl_g6_L3_s44_inc1e2" 6 44 1e-2 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/checkpoints/final_step249675_tok1000000042.pt"
launch_job "pcc_bl_g7_L3_s42_inc0" 7 42 0 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/checkpoints/final_step249244_tok1000000016.pt"

echo "$RUN_ROOT"
