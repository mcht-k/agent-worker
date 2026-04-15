## ZADANIE
Stwórz Hangfire job wysyłający przypomnienie email 7 dni przed wygaśnięciem vouchera.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Vouchers/
- backend/Modules/Vouchify.Modules.Notifications/
- backend/Vouchify.Worker/

## CO ZROBIĆ
1. Stwórz Hangfire job `SendVoucherExpiryRemindersJob` w Worker:
   - Uruchamiany codziennie o 09:00
   - Pobiera vouchery gdzie Status == Active AND ValidUntil == Today + 7 dni AND ReminderSentAt IS NULL
2. Dodaj pole `ReminderSentAt` (nullable DateTime) do encji Voucher + migracja `AddVoucherReminderSentAt`
3. Dla każdego znalezionego vouchera:
   - Wywołaj `INotificationService.SendVoucherExpiryReminderAsync(voucher)`
   - Ustaw `ReminderSentAt = DateTime.UtcNow`
4. Przetwarzaj partiami po 50 voucherów żeby nie przeciążać Resend API
5. Stwórz job `SendMonthlySalesSummaryJob`:
   - Uruchamiany 1. dnia każdego miesiąca o 08:00
   - Pobiera wszystkich Active tenantów
   - Dla każdego tenanta zbiera statystyki poprzedniego miesiąca: liczba zamówień, suma sprzedaży, liczba voucherów
   - Wywołuje `INotificationService.SendMonthlySalesSummaryAsync(tenant, stats)`
6. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Vouchers/ backend/Vouchify.Worker/ backend/Vouchify.Infrastructure/
git commit -m "feat(vouchers): expiry reminder job, monthly sales summary job"
git push
docker compose -f docker-compose.dev.yml up -d --build worker


## DEFINICJA UKOŃCZENIA
- [x] Job ExpiryReminders widoczny w Hangfire dashboard
- [x] ReminderSentAt ustawiony po wysyłce
- [x] Job MonthlySummary widoczny w Hangfire dashboard
- [x] Brak duplikatów przypomnień (ReminderSentAt guard)
## _STATUS
- stan: completed
- ukończony: 2026-04-12
