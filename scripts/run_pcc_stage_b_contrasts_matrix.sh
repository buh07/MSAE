#!/usr/bin/env bash
set -euo pipefail
ROOT="${REPO_ROOT}"
TS="$(date +%Y%m%d_%H%M%S)"
RUN_ROOT="$ROOT/pilot_runs/${TS}_pcc_stage_b_contrasts"
mkdir -p "$RUN_ROOT/logs" "$RUN_ROOT/outputs"
MANIFEST="$RUN_ROOT/run_manifest.tsv"
SESSIONS="$RUN_ROOT/tmux_sessions.txt"
: > "$SESSIONS"
printf 'job_id\tgpu\tseed\tlambda\tcheckpoint_path\toutput_dir\tlog_path\tsession_name\n' > "$MANIFEST"
GIT_HASH="$(cd "$ROOT" && git rev-parse HEAD 2>/dev/null || true)"
launch_job(){
  local job_id="$1" gpu="$2" seed="$3" lam="$4" ckpt="$5"
  local outdir="$RUN_ROOT/outputs/$job_id"
  local logfile="$RUN_ROOT/logs/${job_id}.log"
  local session="pcc-bc-${job_id}-${TS}"
  mkdir -p "$outdir"
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
    echo [start] job=$job_id gpu=$gpu seed=$seed lambda=$lam layer=3 checkpoint=$ckpt
    CUDA_VISIBLE_DEVICES=$gpu python -u '$ROOT/scripts/pcc_stage_b_contrasts.py' \
      --checkpoint_path '$ckpt' \
      --model_name 'EleutherAI/pythia-160m-deduped' \
      --layer_index 3 \
      --seed '$seed' \
      --device cuda \
      --dtype auto \
      --output_dir '$outdir' \
      --git_commit_hash '$GIT_HASH' \
      --context_length 192
    echo [done] job=$job_id
  " > "$logfile" 2>&1
}
launch_job pcc_bc_g4_L3_s42_inc1e2 4 42 1e-2 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g4_L3_s42_inc1e2/checkpoints/final_step249244_tok1000000016.pt"
launch_job pcc_bc_g5_L3_s43_inc1e2 5 43 1e-2 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g5_L3_s43_inc1e2/checkpoints/final_step249244_tok1000000016.pt"
launch_job pcc_bc_g6_L3_s44_inc1e2 6 44 1e-2 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g6_L3_s44_inc1e2/checkpoints/final_step249675_tok1000000042.pt"
launch_job pcc_bc_g7_L3_s42_inc0 7 42 0 "$ROOT/pilot_runs/20260601_132158_k2_msae_wave2_fastdata_stream/outputs/k2_wave2_fast_g7_L3_s42_inc0/checkpoints/final_step249244_tok1000000016.pt"
echo "$RUN_ROOT"
