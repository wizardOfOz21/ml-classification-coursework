# Modular notebook implementation plan

**Goal:** Split the existing notebook for development and rebuild an autonomous generated notebook without changing the original

**Architecture:** Seven ordered section notebooks, a JSON manifest, two source files containing the existing association helpers. Development cells execute source definitions in the shared notebook namespace; the builder replaces only declared module placeholders with their original source at the original position. Development bootstrap cells never enter the build

**Tech stack:** Python, nbformat, nbclient/ipykernel, unittest, existing data-analysis environment

**Spec:** User handoff attached in this conversation, 2026-11-07

## Constraints

- Preserve solution.ipynb and its byte-identical solution.original.ipynb backup
- Preserve all text, attachments, outputs, parameters and execution dependencies
- Do not change analytical methods or repair the original logic
- Generated notebook requires only installed libraries and data/

## Tasks

- [x] Save backup and inventory headings, imports, helpers and output cells
- [x] Test builder: order, exact round-trip source/attachments, edited helper inlining, refusal to overwrite originals, rejection of missing/duplicate modules
- [x] Create section notebooks, manifest, helpers and builder using nbformat
- [x] Test validation: semantic/source mismatch detection, numerical tolerance, plot-data mismatch and original hash checks
- [x] Implement validation in fresh kernels, reproducibly seed only the validation harness, capture displayed tables, final numerical objects and figure data
- [x] Run baseline, generated in data-only directories, and modular sources in a shared clean kernel; compare results and report failures separately from unavailable checks
- [x] Add README, generate validation_report.md, run complete unittest suite and check original hashes

## Review focus

- Bootstrap paths when opening a section under notebooks/
- Helpers referring to notebook globals must retain the same late binding
- Embedded Markdown image attachments must survive
- Unseeded data.sample() and random Styler IDs must not produce false differences
- Failed kernel startup must be reported as unavailable, never as a passing execution

## Decisions

There is no Git repository here; work proceeds in place with preserved originals. No replacement, commit or publication is requested. Execute in this session without an extra approval checkpoint, per the explicit handoff

## Verification record

- 10 unittest cases passed
- Original, generated data-only execution and modular shared-kernel execution passed
- Each run: 24 displayed tables, 13 figures, 136 data objects; no differences
- Repeated build is byte-identical; both originals retain their recorded SHA-256
- Fresh reviewer found two P2 issues (output path protection and conditional integrity wording); both reproduced with failing tests and fixed, all tests green
- Jupyter needs local sockets; final complete checks ran with the required local-kernel permission
