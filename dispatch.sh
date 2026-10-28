#!/bin/bash
# Entrypoint of the UID 140 engine v2 entry: one image, one unchanged REAX reference engine tree per model, picked by
# $REAX_MODEL (the validator starts one container per model). Each tree keeps its own entrypoint, presets and readout.
#   blink text : /opt/reax    = reference engine commit 4230e50 (the pinned Blink text reference ab02e141)
#   jeffan     : /opt/reax-j  = reference engine commit 3582925 (the pinned Jeffan reference e98cc981)
# Our change in both trees: engine/serve.py dispatches every decision to the vLLM client pool at once (X_NOBARRIER=1)
# instead of waiting for a whole step to finish; requests, presets and readout are the reference's.
# Blink text only: vLLM also captures CUDA graphs at the step sizes this traffic produces (1 .. 4096 tokens; the reference's
# default list stops at 64 tokens, so its ~1,400-2,100-token prefill steps run without graphs). Same compiled kernels,
# batch-invariant as in the reference; X_BLINK_CG=0 restores the reference's capture list.
set -u
CG_SIZES='[1,2,4,8,16,24,32,40,48,56,64,96,128,192,256,384,512,640,768,896,1024,1152,1280,1408,1536,1664,1792,1920,2048,2304,2560,2816,3072,3584,4096]'

export REAX_MODEL=${REAX_MODEL:-blink-v0.3-26b-a4b}
case "$REAX_MODEL" in
  blink|s1-fast-2|blink-v0.3-26b-a4b) export PYTHONPATH=/opt/reax
    if [ "${X_BLINK_CG:-1}" = 1 ]; then
      export REAX_VLLM_EXTRA="${REAX_VLLM_EXTRA:-} --compilation-config {\"cudagraph_capture_sizes\":${CG_SIZES},\"max_cudagraph_capture_size\":4096}"
    fi
    exec /opt/reax/entrypoint.sh ;;
  jeffan|jeffan-31b-1710) export PYTHONPATH=/opt/reax-j; exec /opt/reax-j/entrypoint.sh ;;
  *) echo "reax: model ${REAX_MODEL} is not served by this engine (declared: blink, jeffan)"; exit 2 ;;
esac
