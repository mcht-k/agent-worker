#!/bin/bash
# status.sh — wyświetla stan kolejki tasków agenta

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

QUEUE=".agent/queue.md"
LAST_RUN=".agent/last-run-result.txt"

if [ ! -f "$QUEUE" ]; then
  echo "Brak pliku kolejki: $QUEUE"
  exit 1
fi

python3 - "$QUEUE" "$LAST_RUN" <<'PYEOF'
import sys, re, os
from datetime import datetime

queue_file = sys.argv[1]
last_run_file = sys.argv[2]

# ANSI
GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
RED    = '\033[0;31m'
GRAY   = '\033[0;37m'
BLUE   = '\033[0;34m'
BOLD   = '\033[1m'
NC     = '\033[0m'

STATUS_COLORS = {
    'completed':          GREEN,
    'in_progress':        YELLOW,
    'failed':             RED,
    'pending':            GRAY,
    'needs_continuation': BLUE,
}

STATUS_ICONS = {
    'completed':          '✅',
    'in_progress':        '🔄',
    'failed':             '❌',
    'pending':            '⏳',
    'needs_continuation': '⏸️ ',
}

# Nagłówek
print(f"\n{BOLD}Vouchify Agent — Status kolejki{NC}")
print("=" * 70)
print(f"{BOLD}{'Kol.':<6} {'Task':<35} {'Status':<22} {'_STATUS':<10}{NC}")
print("-" * 70)

# Zliczanie
counts = {}
tasks_data = []

with open(queue_file) as f:
    for line in f:
        m = re.match(r'\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(\w+)\s*\|', line)
        if m:
            num, task_path, status = m.group(1), m.group(2), m.group(3)
            tasks_data.append((num, task_path, status))
            counts[status] = counts.get(status, 0) + 1

for num, task_path, status in tasks_data:
    task_name = task_path.replace('tasks/', '').replace('.md', '')
    color = STATUS_COLORS.get(status, NC)
    icon = STATUS_ICONS.get(status, '  ')

    # Odczytaj _STATUS z pliku taska
    task_file_status = ''
    full_path = os.path.join('.agent', task_path)
    if os.path.exists(full_path):
        try:
            with open(full_path) as tf:
                content = tf.read()
            ms = re.search(r'## _STATUS\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
            if ms:
                block = ms.group(1)
                # Wyodrębnij timestamp ukończenia lub notatki
                ts_m = re.search(r'- ukończony: (.+)', block)
                st_m = re.search(r'- stan: (.+)', block)
                if ts_m:
                    task_file_status = ts_m.group(1).strip()[:16]  # "YYYY-MM-DD HH:MM"
                elif st_m:
                    task_file_status = st_m.group(1).strip()
        except Exception:
            pass

    print(f"{color}{num:<6} {task_name:<35} {icon} {status:<20} {task_file_status}{NC}")

# Podsumowanie
print("-" * 70)
summary_parts = []
for s, c in sorted(counts.items()):
    color = STATUS_COLORS.get(s, NC)
    icon = STATUS_ICONS.get(s, '  ')
    summary_parts.append(f"{color}{icon} {s}: {c}{NC}")
print("  ".join(summary_parts))

# Ostatnie wykonanie
print()
if os.path.exists(last_run_file):
    print(f"{BOLD}Ostatnie wykonanie:{NC}")
    try:
        with open(last_run_file) as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, val = line.split('=', 1)
                    if key == 'task':
                        print(f"  Task:      {val}")
                    elif key == 'timestamp':
                        print(f"  Czas:      {val}")
                    elif key == 'all_checkboxes_checked':
                        checked_str = f"{GREEN}tak{NC}" if val == 'true' else f"{RED}nie{NC}"
                        print(f"  Checkboxy: {checked_str}")
                    elif key == 'exit_status':
                        ok_str = f"{GREEN}{val}{NC}" if val == 'success' else f"{RED}{val}{NC}"
                        print(f"  Wynik:     {ok_str}")
    except Exception as e:
        print(f"  (błąd odczytu: {e})")
else:
    print(f"{GRAY}Brak danych ostatniego wykonania (.agent/last-run-result.txt){NC}")

# Legenda
print()
print(f"Legenda: {GREEN}completed{NC} | {YELLOW}in_progress{NC} | {RED}failed{NC} | {GRAY}pending{NC} | {BLUE}needs_continuation{NC}")
print()
PYEOF
