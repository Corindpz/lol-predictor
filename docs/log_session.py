"""
Utilitaire pour logger une sortie de terminal dans docs/progress/.

Usage :
    python src/data/pull_matches.py --count 500 | python docs/log_session.py "pull_500_matchs"
    python src/models/train.py | python docs/log_session.py "premier_entrainement"
"""

import sys
from datetime import datetime
from pathlib import Path

label = sys.argv[1] if len(sys.argv) > 1 else "run"
date = datetime.now().strftime("%Y-%m-%d")
ts = datetime.now().strftime("%H%M%S")

output_dir = Path("docs/progress")
output_dir.mkdir(parents=True, exist_ok=True)

output_path = output_dir / f"{date}_{label}_{ts}.txt"
content = sys.stdin.read()

output_path.write_text(content)
print(content, end="")
print(f"\n[log_session] Sauvegardé → {output_path}", file=sys.stderr)
