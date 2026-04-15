## ZADANIE
Dodaj testy jednostkowe i integracyjne dla aktualnej implementacji backendu — zacznij od modułów z największym ryzykiem biznesowym.

## PLIKI DO PRZECZYTANIA
- backend/Modules/
- tests/Vouchify.Tests.Unit/
- tests/Vouchify.Tests.Integration/
- docs/security-review.md

## CO ZROBIĆ
1. Sprawdź co już istnieje w tests/ — nie duplikuj istniejących testów

2. Dodaj testy jednostkowe w Vouchify.Tests.Unit dla: generowania kodu vouchera (unikalność, format XXXX-XXXX-XXXX), obliczania ValidUntil (tryb dni vs konkretna data), walidacji FluentValidation dla CreateVoucherTypeCommand i CreateCheckoutSessionCommand, logiki zmiany statusów tenanta (draft, configured, stripe_pending, active), RedeemVoucherCommand (walidacja statusu AlreadyUsed i Expired)

3. Dodaj testy integracyjne w Vouchify.Tests.Integration dla: flow zakupu end-to-end (checkout, webhook checkout.session.completed, voucher created), weryfikacji vouchera (verify, redeem, verify ponownie z błędem AlreadyUsed), izolacji multi-tenant (tenant A nie widzi danych tenanta B), idempotentności webhooka Stripe (ten sam EventId dwa razy)

4. Użyj istniejących konwencji z tests/ — nie wprowadzaj nowych frameworków bez potrzeby

5. Uruchom testy: cd backend && dotnet test 2>&1 | tail -20

6. Po zakończeniu zaznacz wszystkie checkboxy w sekcji DEFINICJA UKOŃCZENIA na [x]

## PO WYKONANIU
cd ~/projects/vouchify-mono
git add tests/
git commit -m "test: unit and integration tests for core business logic"
git push

## DEFINICJA UKOŃCZENIA
- [x] Testy jednostkowe dla generowania kodu vouchera
- [x] Testy jednostkowe dla walidacji komend
- [x] Testy jednostkowe dla logiki statusów tenanta
- [x] Test integracyjny flow zakupu end-to-end
- [x] Test integracyjny izolacji multi-tenant
- [x] Test integracyjny idempotentności webhooków
- [x] dotnet test przechodzi bez błędów
- [x] Commit i push wykonany
## _STATUS
- stan: completed
- ukończony: 2026-04-12 16:45:08
