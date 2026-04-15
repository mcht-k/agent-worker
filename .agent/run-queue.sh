#!/bin/bash
# run-queue.sh — automatyczne kolejkowanie tasków agenta
# Użycie: nohup .agent/run-queue.sh > .agent/agent.log 2>&1 &

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

QUEUE=".agent/queue.md"
LOG=".agent/agent.log"
LOCK_FILE="/tmp/vouchify-queue.lock"

# ─── Zabezpieczenie przed równoległymi instancjami ────────────────────────────
if [ -f "$LOCK_FILE" ]; then
  existing_pid=$(cat "$LOCK_FILE" 2>/dev/null)
  if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "=== [queue] $(date '+%Y-%m-%d %H:%M:%S'): Inna instancja już działa (PID $existing_pid) — kończę ===" >&2
    exit 0
  fi
fi
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT INT TERM

# Ścieżka do pliku taska (queue przechowuje "tasks/foo.md", pliki są w ".agent/tasks/foo.md")
full_path() { echo ".agent/$1"; }

# Załaduj NOTIFY_URL z ~/.bashrc
# shellcheck disable=SC1090
[ -f ~/.bashrc ] && source ~/.bashrc 2>/dev/null || true

notify() {
  [ -n "${NOTIFY_URL:-}" ] && curl -s -d "$1" "$NOTIFY_URL" > /dev/null 2>&1 || true
}

log() {
  echo "=== [queue] $(date '+%Y-%m-%d %H:%M:%S'): $1 ===" | tee -a "$LOG"
}

# ─── Parsowanie queue.md ───────────────────────────────────────────────────────

# Pobierz wszystkie taski jako "num\ttask_path\tstatus"
get_all_tasks() {
  python3 - "$QUEUE" <<'PYEOF'
import sys, re
with open(sys.argv[1]) as f:
    for line in f:
        m = re.match(r'\|\s*(\d+)\s*\|\s*(\S+)\s*\|\s*(\w+)\s*\|', line)
        if m:
            print(f"{m.group(1)}\t{m.group(2)}\t{m.group(3)}")
PYEOF
}

# Pobierz status taska z queue.md
get_status() {
  python3 - "$1" "$QUEUE" <<'PYEOF'
import sys, re
task, queue = sys.argv[1], sys.argv[2]
with open(queue) as f:
    for line in f:
        m = re.match(r'\|\s*\d+\s*\|\s*' + re.escape(task) + r'\s*\|\s*(\w+)\s*\|', line)
        if m:
            print(m.group(1)); break
PYEOF
}

# Zaktualizuj status taska w queue.md
set_queue_status() {
  local task_path="$1" new_status="$2"
  python3 - "$task_path" "$new_status" "$QUEUE" <<'PYEOF'
import sys, re
task, status, queue = sys.argv[1], sys.argv[2], sys.argv[3]
with open(queue) as f:
    lines = f.readlines()
result = []
for line in lines:
    m = re.match(r'(\|\s*\d+\s*\|\s*' + re.escape(task) + r'\s*\|\s*)\w+(\s*\|.*)', line)
    if m:
        line = m.group(1) + status + m.group(2).rstrip('\n') + '\n'
    result.append(line)
with open(queue, 'w') as f:
    f.writelines(result)
PYEOF
}

# Pobierz zależności taska (numery oddzielone przecinkami lub pusty string)
get_deps() {
  python3 - "$1" "$QUEUE" <<'PYEOF'
import sys, re
task, queue = sys.argv[1], sys.argv[2]
with open(queue) as f:
    for line in f:
        m = re.match(r'\|\s*\d+\s*\|\s*' + re.escape(task) + r'\s*\|\s*\w+\s*\|\s*([^|]+)\s*\|', line)
        if m:
            deps = m.group(1).strip()
            if deps and deps not in ('—', '-'):
                print(deps)
            break
PYEOF
}

# Pobierz ścieżkę taska (queue-relative) po numerze kolejności
get_task_by_num() {
  python3 - "$1" "$QUEUE" <<'PYEOF'
import sys, re
num, queue = sys.argv[1], sys.argv[2]
with open(queue) as f:
    for line in f:
        m = re.match(r'\|\s*' + re.escape(num) + r'\s*\|\s*(\S+)\s*\|', line)
        if m:
            print(m.group(1)); break
PYEOF
}

# ─── Obsługa pliku taska ──────────────────────────────────────────────────────

# Zaktualizuj sekcję ## _STATUS w pliku taska
update_task_file_status() {
  local fs_path="$1" state="$2" note="${3:-}"
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')

  python3 - "$fs_path" "$state" "$note" "$ts" <<'PYEOF'
import sys, re
fs_path, state, note, ts = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
try:
    with open(fs_path) as f:
        content = f.read()
    lines = [f"- stan: {state}"]
    lines.append(f"- rozpoczęty: {ts}" if state == 'in_progress' else f"- ukończony: {ts}")
    if note:
        lines.append(f"- notatka: {note}")
    new_block = "\n## _STATUS\n" + "\n".join(lines) + "\n"
    content = re.sub(r'\n## _STATUS\n.*?(?=\n## |\Z)', '', content, flags=re.DOTALL)
    content = content.rstrip() + new_block
    with open(fs_path, 'w') as f:
        f.write(content)
except Exception as e:
    print(f"Błąd aktualizacji _STATUS: {e}", file=sys.stderr)
PYEOF
}

# Sprawdź czy w ## STATUS są niezaznaczone checkboxy
has_unchecked_boxes() {
  grep -q -- '- \[ \]' "$1" 2>/dev/null
}

# ─── Logika zależności ────────────────────────────────────────────────────────

deps_satisfied() {
  local task_path="$1"
  local deps
  deps=$(get_deps "$task_path")
  [ -z "$deps" ] && return 0

  IFS=',' read -ra dep_nums <<< "$deps"
  for dep_num in "${dep_nums[@]}"; do
    dep_num=$(echo "$dep_num" | tr -d ' ')
    local dep_task dep_status
    dep_task=$(get_task_by_num "$dep_num")
    [ -z "$dep_task" ] && continue
    dep_status=$(get_status "$dep_task")
    [ "$dep_status" != "completed" ] && return 1
  done
  return 0
}

# Sprawdź czy są jeszcze taski wymagające działania (pending/in_progress/needs_continuation/failed)
has_active_tasks() {
  while IFS=$'\t' read -r num task status; do
    if [ "$status" = "pending" ] || [ "$status" = "in_progress" ] || \
       [ "$status" = "needs_continuation" ] || [ "$status" = "failed" ]; then
      return 0
    fi
  done < <(get_all_tasks)
  return 1
}

# ─── Główna logika ────────────────────────────────────────────────────────────

main() {
  log "Startuję run-queue.sh"

  local target_task="" fs_path="" run_mode="normal"

  # Priorytet 1: task z statusem in_progress → wznów z --continue
  while IFS=$'\t' read -r num task status; do
    if [ "$status" = "in_progress" ]; then
      target_task="$task"
      run_mode="continue"
      log "Wznawianie in_progress taska: $task"
      break
    fi
  done < <(get_all_tasks)

  # Priorytet 2: task z statusem needs_continuation → wznów z --continue
  if [ -z "$target_task" ]; then
    while IFS=$'\t' read -r num task status; do
      if [ "$status" = "needs_continuation" ]; then
        target_task="$task"
        run_mode="continue"
        log "Wznawianie needs_continuation taska: $task"
        break
      fi
    done < <(get_all_tasks)
  fi

  # Priorytet 3: task z statusem failed → wznów normalnie (bez --continue)
  if [ -z "$target_task" ]; then
    while IFS=$'\t' read -r num task status; do
      if [ "$status" = "failed" ]; then
        target_task="$task"
        run_mode="normal"
        log "Wznawianie failed taska: $task"
        break
      fi
    done < <(get_all_tasks)
  fi

  # Priorytet 4: pierwszy pending z ukończonymi zależnościami → uruchom normalnie
  if [ -z "$target_task" ]; then
    while IFS=$'\t' read -r num task status; do
      if [ "$status" = "pending" ]; then
        if deps_satisfied "$task"; then
          target_task="$task"
          run_mode="normal"
          log "Wybrany task: $task"
          break
        else
          log "Task $task: zależności niezukończone — pomijam"
        fi
      fi
    done < <(get_all_tasks)
  fi

  # Brak tasków do wykonania
  if [ -z "$target_task" ]; then
    local has_pending=false
    while IFS=$'\t' read -r num task status; do
      if [ "$status" = "pending" ] || [ "$status" = "in_progress" ] || [ "$status" = "needs_continuation" ] || [ "$status" = "failed" ]; then
        has_pending=true; break
      fi
    done < <(get_all_tasks)

    if ! $has_pending; then
      log "Wszystkie taski ukończone!"
      notify "✅ Vouchify: wszystkie taski ukończone"
    else
      log "Brak tasków gotowych do wykonania (oczekujące zależności)"
    fi
    exit 0
  fi

  fs_path=$(full_path "$target_task")
  local task_name
  task_name=$(basename "$target_task" .md)

  # Oznacz jako in_progress
  log "Uruchamiam task: $task_name ($fs_path) [tryb: $run_mode]"
  set_queue_status "$target_task" "in_progress"
  update_task_file_status "$fs_path" "in_progress"

  # Uruchom run.sh (przekaż pełną ścieżkę do pliku i tryb)
  local exit_code=0
  bash .agent/run.sh "$fs_path" "$run_mode" || exit_code=$?

  # Oceń wynik
  local new_status note=""

  if [ $exit_code -ne 0 ]; then
    new_status="failed"
    note="run.sh zakończył się z kodem $exit_code"
    log "Task $task_name: FAILED (exit code $exit_code)"
  elif has_unchecked_boxes "$fs_path"; then
    new_status="needs_continuation"
    note="osiągnięto limit kontekstu"
    log "Task $task_name: NEEDS_CONTINUATION (niezaznaczone checkboxy w ## STATUS)"
  else
    new_status="completed"
    log "Task $task_name: COMPLETED"
  fi

  # Zapisz wynik
  set_queue_status "$target_task" "$new_status"
  update_task_file_status "$fs_path" "$new_status" "$note"

  # Powiadomienia i dalsza akcja
  if [ "$new_status" = "completed" ] || [ "$new_status" = "failed" ]; then
    # Znajdź następny kandydat (do powiadomienia)
    local next_task="" next_name="brak"
    while IFS=$'\t' read -r num task status; do
      if [ "$status" = "pending" ] && deps_satisfied "$task"; then
        next_task="$task"; break
      fi
    done < <(get_all_tasks)
    [ -n "$next_task" ] && next_name=$(basename "$next_task" .md)

    if [ "$new_status" = "completed" ]; then
      notify "✅ Vouchify: $task_name ukończony, następny: $next_name"
    else
      notify "❌ Vouchify: $task_name FAILED, następny: $next_name"
    fi

    log "Przechodzę do następnego taska..."
    if ! has_active_tasks; then
      log "Wszystkie taski ukończone!"
      notify "✅ Vouchify: wszystkie taski ukończone"
      exit 0
    fi
    exec bash .agent/run-queue.sh

  else
    # needs_continuation — kontynuuj automatycznie (nie zatrzymuj kolejki)
    log "Task $task_name wymaga kontynuacji — wznawiam automatycznie..."
    notify "⏸️ Vouchify: $task_name wymaga kontynuacji — wznawiam"
    if ! has_active_tasks; then
      log "Wszystkie taski ukończone!"
      notify "✅ Vouchify: wszystkie taski ukończone"
      exit 0
    fi
    exec bash .agent/run-queue.sh
  fi
}

main "$@"
