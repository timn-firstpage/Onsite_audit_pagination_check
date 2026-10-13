"""Package runtime resources only, under a discoverable skill folder name."""
import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
FILES = ['SKILL.md', 'README.md', 'config.template.json', 'agents/openai.yaml',
         'references/audit-rules.md', 'references/exports.md', 'references/shared-config.md',
         'references/output-contract.md', 'scripts/audit.py', 'scripts/build_report.mjs']

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, 'x', compression=ZIP_DEFLATED) as archive:
        for name in FILES:
            archive.write(ROOT / name, 'onsite-audit-pagination/' + name)
    print(args.output.resolve())
