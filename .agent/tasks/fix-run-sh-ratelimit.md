## ZADANIE
Napraw błąd w .agent/run.sh gdzie grep sprawdzający rate limit czyta cały log zamiast tylko output bieżącego wywołania claude, co powoduje fałszywe wykrycie limitu.

## PLIKI DO PRZECZYTANIA
- .agent/run.sh

## CO ZROBIĆ
1. Zmień logikę wywołania claude tak żeby output każdego wywołania był zapisywany do tymczasowego pliku `/tmp/claude-output-$$.txt` (gdzie `$$` to PID procesu), a dopiero potem dopisywany do LOG
2. Grep wykrywający limit sprawdzaj na `/tmp/claude-output-$$.txt` zamiast `tail -20 "$LOG"`
3. Wyczyść plik tymczasowy `rm -f /tmp/claude-output-$$.txt` przed każdym kolejnym wywołaniem claude w pętli retry
4. Na końcu skryptu (zarówno przy success jak i max_retries) usuń plik tymczasowy

Konkretna zmiana — zastąp:
```bash
claude -p --dangerously-skip-permissions < "$TASK_FILE" 2>&1 | tee -a "$LOG"
```
czymś w stylu:
```bash
CLAUDE_OUT="/tmp/claude-output-$$.txt"
claude -p --dangerously-skip-permissions < "$TASK_FILE" 2>&1 | tee "$CLAUDE_OUT" | tee -a "$LOG"
```
i w pętli while sprawdzaj `grep -qi "limit\|rate\|quota\|429\|paused" "$CLAUDE_OUT"` zamiast `tail -20 "$LOG"`
5. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU
```
cd ~/projects/vouchify-mono
git add .agent/run.sh
git commit -m "fix(agent): rate limit detection on current output only, not full log"
git push
```

## DEFINICJA UKOŃCZENIA
- [x] grep rate limit sprawdza tylko output bieżącego wywołania claude
- [x] plik tymczasowy czyszczony przed każdym retry
- [x] plik tymczasowy usuwany po zakończeniu skryptu

## _STATUS
- stan: completed
- ukończony: 2026-04-11 00:00:00
- notatka: commit 5be4ffc — fix(agent): rate limit detection on current output only, not full log
