# reax-eng-v2: SN92 engine track v2 entry of UID 140

Source:  https://github.com/flextra19/reax-eng-v2  (this file is IMAGE-README.md there; the image labels
         ai.reax.engine.commit / org.opencontainers.image.revision name the exact commit)
Hotkey:  5GWdcbe5w4GNPK5eFp8DkoVbBSAGBtZ9GeFvwvR9gkFAbM3z (UID 140)
Models:  blink, jeffan (ai.reax.engine.models)
Parents: none. The bases are the REAX reference images:
         ghcr.io/reaxlabs/reax-engine-ref-blink@sha256:ab02e141ffb5672dc68e137736be0a6fa15445c7cc824a51f6ad2a6664c0e10a (engine 4230e50)
         ghcr.io/reaxlabs/reax-engine-ref-jeffan@sha256:e98cc981a40013d243de6ea65147b823fc9cfb5655a00859dbc8de327b2634d6 (engine 3582925)
Natives: none added (only Python and shell files). Weight-like data: none added.

Files of ours in this image (byte-identical to the repository):
  /opt/reax/engine/serve.py    = serve_blink.py   (reference serve.py of 4230e50 + the X_NOBARRIER block)
  /opt/reax-j/engine/serve.py  = serve_jeffan.py  (reference serve.py of 3582925 + the X_NOBARRIER block)
  /opt/reax/dispatch.sh        = dispatch.sh      (entrypoint: picks the tree by $REAX_MODEL)
  /README.md                   = IMAGE-README.md  (this file)
/opt/reax-j is /opt/reax of the Jeffan reference image without engine/scales. Licences: /licenses.

Change: serve.py hands every queued decision straight to the vLLM client pool (same _one, same request, same vLLM
flags, presets and readout as the reference) instead of waiting for the whole step (pool.map) to finish.
