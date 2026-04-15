#!/bin/bash
TASK_FILE="${1:-.agent/current-task.md}"
RUN_MODE="${2:-normal}"
LOG=".agent/agent.log"
LAST_RUN=".agent/last-run-result.txt"
MAX_RETRIES=48
RETRY_WAIT=1800

notify() {
  [ -n "$NOTIFY_URL" ] && curl -s -d "$1" "$NOTIFY_URL" > /dev/null
}

# Sprawdź czy wszystkie checkboxy w ## STATUS są zaznaczone
check_all_boxes() {
  local file="$1"
  if grep -q -- '- \[ \]' "$file" 2>/dev/null; then
    echo "false"
  else
    echo "true"
  fi
}

write_result() {
  local status="$1"
  local all_checked
  all_checked=$(check_all_boxes "$TASK_FILE")
  {
    echo "task=$TASK_FILE"
    echo "timestamp=$(date '+%Y-%m-%d %H:%M:%S')"
    echo "all_checkboxes_checked=$all_checked"
    echo "exit_status=$status"
  } > "$LAST_RUN"
}

CLAUDE_OUT="/tmp/claude-output-$$.txt"

echo "=== START: $(date) ===" | tee -a "$LOG"
notify "🚀 Vouchify agent startuje: $(basename $TASK_FILE) [tryb: $RUN_MODE]"

rm -f "$CLAUDE_OUT"

# Pierwsze uruchomienie: użyj --continue jeśli RUN_MODE=continue
if [ "$RUN_MODE" = "continue" ]; then
  cat "$TASK_FILE" | claude -p --continue --dangerously-skip-permissions 2>&1 | tee "$CLAUDE_OUT" | tee -a "$LOG"
else
  cat "$TASK_FILE" | claude -p --dangerously-skip-permissions 2>&1 | tee "$CLAUDE_OUT" | tee -a "$LOG"
fi

ATTEMPT=0
while [ $ATTEMPT -lt $MAX_RETRIES ]; do
  if grep -q "You've hit your limit" "$CLAUDE_OUT" 2>/dev/null; then
    ATTEMPT=$((ATTEMPT + 1))
    echo "=== Limit hit ($ATTEMPT/$MAX_RETRIES), czekam ${RETRY_WAIT}s: $(date) ===" | tee -a "$LOG"
    notify "⏳ Limit hit ($ATTEMPT/$MAX_RETRIES) – wznowienie za 30 min"
    sleep $RETRY_WAIT
    echo "=== Wznawiam: $(date) ===" | tee -a "$LOG"
    notify "🔄 Wznawiam pracę..."
    rm -f "$CLAUDE_OUT"
    cat "$TASK_FILE" | claude -p --continue --dangerously-skip-permissions 2>&1 | tee "$CLAUDE_OUT" | tee -a "$LOG"
  else
    echo "=== UKOŃCZONO: $(date) ===" | tee -a "$LOG"
    notify "✅ Agent ukończył zadanie: $(basename $TASK_FILE)"
    write_result "success"
    cd ~/projects/vouchify-mono && git push origin main 2>&1 | tee -a "$LOG" || true
    rm -f "$CLAUDE_OUT"
    exit 0
  fi
done

echo "=== MAX_RETRIES przekroczony: $(date) ===" | tee -a "$LOG"
notify "❌ Agent zatrzymany – przekroczono MAX_RETRIES"
write_result "max_retries"
rm -f "$CLAUDE_OUT"
exit 1
