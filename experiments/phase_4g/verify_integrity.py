"""Re-verify the Phase 4G integrity baseline after implementation.

Checks every file recorded in ``experiments/phase_4g/baseline_integrity.json``
against its recorded size and SHA-256, re-runs the BANC manifest verification,
and confirms that nothing is staged in git.

Output: ``experiments/results/phase_4g/integrity_recheck.json``.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain.banc_graph import OUT_DIR, verify_manifest  # noqa: E402

BASELINE = PROJECT_ROOT / "experiments" / "phase_4g" / "baseline_integrity.json"
BANC_MANIFEST = OUT_DIR / "banc_manifest.json"
OUTPUT = PROJECT_ROOT / "experiments" / "results" / "phase_4g" / "integrity_recheck.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    entries = []
    for relative, expected in baseline.items():
        path = PROJECT_ROOT / relative
        exists = path.is_file()
        size = path.stat().st_size if exists else None
        actual = sha256_file(path) if exists else None
        entries.append(
            {
                "path": relative,
                "expected_bytes": expected.get("bytes"),
                "actual_bytes": size,
                "expected_sha256": expected.get("sha256"),
                "actual_sha256": actual,
                "exists": exists,
                "size_match": size == expected.get("bytes"),
                "hash_match": actual == expected.get("sha256"),
            }
        )
    failures = [
        entry["path"]
        for entry in entries
        if not (entry["exists"] and entry["size_match"] and entry["hash_match"])
    ]

    manifest = json.loads(BANC_MANIFEST.read_text(encoding="utf-8"))
    manifest_check = verify_manifest(manifest, PROJECT_ROOT)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if staged.returncode != 0:
        raise RuntimeError(staged.stderr.strip())
    staged_files = [line for line in staged.stdout.splitlines() if line.strip()]

    payload = {
        "phase": "4G-final",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "baseline": str(BASELINE.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "protected_files_total": len(entries),
        "protected_files_matching": len(entries) - len(failures),
        "protected_files_failed": failures,
        "baseline_pass": not failures,
        "banc_manifest": {
            "path": str(BANC_MANIFEST.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "checks": manifest_check["checks"],
            "failures": manifest_check["failures"],
            "pass": manifest_check["pass"],
        },
        "staged_files": staged_files,
        "nothing_staged": not staged_files,
        "verdict": "PASS"
        if not failures and manifest_check["pass"] and not staged_files
        else "FAIL",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "protected_files": len(entries),
                "protected_failed": failures,
                "banc_manifest_pass": manifest_check["pass"],
                "banc_manifest_failures": manifest_check["failures"],
                "staged_files": staged_files,
                "verdict": payload["verdict"],
                "output": str(OUTPUT.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
