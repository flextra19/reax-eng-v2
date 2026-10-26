#!/bin/bash
# Entrypoint of the UID 140 engine v2 entry: one image, one unchanged REAX reference engine tree per model, picked by
# $REAX_MODEL (the validator starts one container per model). Each tree keeps its own entrypoint, presets and readout.
#   blink text : /opt/reax    = reference engine commit 4230e50 (the pinned Blink text reference ab02e141)
#   jeffan     : /opt/reax-j  = reference engine commit 3582925 (the pinned Jeffan reference e98cc981)
# Our change in both trees: engine/serve.py dispatches every decision to the vLLM client pool at once (X_NOBARRIER=1)
# instead of waiting for a whole step to finish; vLLM flags, requests and readout are the reference's.
set -u
export REAX_MODEL=${REAX_MODEL:-blink-v0.3-26b-a4b}
case "$REAX_MODEL" in
  blink|s1-fast-2|blink-v0.3-26b-a4b) export PYTHONPATH=/opt/reax; exec /opt/reax/entrypoint.sh ;;
  jeffan|jeffan-31b-1710) export PYTHONPATH=/opt/reax-j; exec /opt/reax-j/entrypoint.sh ;;
  *) echo "reax: model ${REAX_MODEL} is not served by this engine (declared: blink, jeffan)"; exit 2 ;;
esac
