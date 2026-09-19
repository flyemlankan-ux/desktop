# Real compiled app-only delivery proof

12 checks passed using compiled `0d0b370` and `0c2b163` apps. The current production manager ran real signature, exact archived-source asset, privacy, process/open-file and no-overwrite checks. No verification/activity/publishing functions were replaced.

Reproduce while every Zen Terminal app is closed, with a new receipt filename:

```sh
python3 scripts/terminal-tabs/test-terminal-compiled-delivery.py \
  --older .terminal-test/compiled-0d0b370 \
  --newer .terminal-test/compiled-0c2b163 \
  --receipt docs/proof/2026-09-19/compiled-app-delivery-lifecycle.json
```

The script checks dry-run, older install, newer upgrade, explicit rollback refusal/acknowledgement, app-only removal, retained copies and source immutability. JSON records identities, byte/mode snapshot hashes and outcomes. The captured log is empty because successful verification commands are silent; the process exited 0.

The older source archive lacked the new pristine Firefox156 SessionStore/Tabbrowser fixtures. Only those test inputs were copied into that archive, so the current verifier could apply the **older archive's own patches**. No source patch, packaged resource or original compiled app was changed.

All app copies were created under one unique `.terminal-test/compiled-delivery-*` directory. At most four roughly367MB app trees were present transiently (under1.5GB); only this disposable directory was cleaned afterward, including its retained test backups. Both original compiled app hashes were unchanged and free space returned to5.3GiB.

This is app-file replacement proof, not profile upgrade/downgrade compatibility, installed-app UI acceptance, notarization, or proof of the later d29e852 source. No browser was launched; no profile or `/Applications` data was accessed or changed. Next: high-reasoning focused final-package native journeys, with rollback profile compatibility kept separate.
