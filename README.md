# RestoreProof 0.1

File-level backup recovery verification for THREWS ODYSSEY 2026.

**Participant:** Mohit Tiwari, Assistant Professor, Department of Computer Science and Engineering, Bharati Vidyapeeth's College of Engineering, New Delhi, India.

## Demo video

[Watch or download the 55-second demo](demo/RestoreProof_Demo.mp4).

The silent, captioned video displays outputs from actual CLI runs. It is not a browser screen recording. See `evidence/video-run-log.json` for the commands, exit codes and reports used to make it. Browser interaction has not been verified; see `evidence/VALIDATION.md`.

## Quick start (Ubuntu / Windows / macOS)

Requires Python 3.10 or later. No third-party Python packages, API keys, cloud account or internet connection are required for the application.

1. Extract this folder.
2. Open a terminal inside it.
3. Run `python3 server.py` (Windows: `py server.py`).
4. Open http://127.0.0.1:8765 in your browser.
5. Choose a scenario and click **Run recovery drill**.
6. Review per-file results and download JSON evidence.

Stop with Ctrl+C. The server binds to localhost only. Do not deploy this development server on a public interface.

## Use your own files

Create a trusted reference manifest BEFORE the source is lost or modified. Store the manifest independently of the backup; its integrity is an external trust assumption.

```
python3 restoreproof.py manifest /path/to/source /path/outside/source/manifest.json
python3 restoreproof.py verify manifest.json backup.zip --output report.json
```

ZIP entries must be relative to the source directory (no enclosing top-level folder). Outputs use exclusive creation and never overwrite an existing report. Exit codes: 0 = passed; 2 = recovery mismatch; 1 = invalid input/error. The manifest command stores metadata only, not file contents. The dashboard accepts an existing manifest and ZIP; it does not create a backup or generate a manifest from local browser folders.

Dashboard compressed ZIP limit: 16 MiB; manifest upload limit: 4 MiB. Engine limits: 10,000 archive entries and 256 MiB uncompressed contents. Only regular files and directories are supported. Symlinks, traversal paths, noncanonical names, duplicate entries and encrypted ZIPs are rejected. No archive contents are executed. Extraction takes place in a new temporary directory and is deleted at the end of each run. This directory is not an operating-system security sandbox.

## Reproduce the evaluation

```
python3 -m unittest -v
python3 demo.py
```

`demo.py` generates eight synthetic files, five ZIP scenarios, reference manifests and real JSON/HTML verification reports under `evidence/`. No real student data is included. Each run performs actual extraction and rehashing; timings are measured rather than hard-coded. Timings vary across runs and the tiny test corpus is not a production RTO benchmark.

Pass requires every expected file to match both its recorded size and SHA-256 digest, with no unexpected files. Missing and modified files are counted separately. File completeness = verified files / expected files. Byte completeness uses expected bytes; it is null when all expected files are empty. Unexpected files cause FAIL even when file completeness is 100%.

## Scope and limitations

A PASS establishes byte agreement with the supplied trusted manifest for the tested archive. It does not prove malware absence, application correctness, database consistency, bootability, backup freshness, enterprise readiness, legal compliance or future recoverability. The tool cannot recover bytes that are absent or repair corrupt backups. It cannot detect simultaneous tampering with both backup and manifest. It does not provide authenticated signatures, malware scanning, cloud backup connectors or VM recovery.

Existing tools already perform recovery verification. RestoreProof makes no first-of-its-kind claim and is not claimed to outperform enterprise backup software. Its intended contribution is an accessible local demonstration, a small dependency-free implementation, controlled fault injection and clear file-level evidence for small teams and teaching labs. No comparative performance study or user study has been conducted.

## Related tools (documentation consulted 25 October 2026)

- Veeam SureBackup: https://helpcenter.veeam.com/docs/vbr/userguide/agents_recovery_verification.html
- restic restore verification: https://github.com/restic/restic/blob/master/doc/050_restore.rst
- Python ZIP support: https://docs.python.org/3/library/zipfile.html
- Python hashing: https://docs.python.org/3/library/hashlib.html

Veeam and restic are contextual references, not dependencies. No code was copied from them. Python's standard library supplies ZIP, hashing, HTTP and temporary-file functions. Source was generated with OpenAI ChatGPT assistance and tested in this session. The participant must review and understand the code before making the submission declaration. No claim is made that Mohit manually authored every line.

## Package contents

- `restoreproof.py`: verifier and manifest CLI
- `server.py`, `index.html`: local dashboard
- `demo.py`: deterministic synthetic fixtures and scenario generator
- `test_restoreproof.py`: automated correctness and input-safety tests
- `evidence/`: recorded reports, fixtures and test logs
- `SUBMISSION.txt`: form text and publication checklist
- `DEMO_SCRIPT.txt`: suggested spoken explanation

## License

MIT, see LICENSE. Review independently before use with important data.
