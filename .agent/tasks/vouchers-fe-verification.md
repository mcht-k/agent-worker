## ZADANIE
Stwórz widok weryfikacji i realizacji voucherów w Angular — dostępny dla roli employee i owner.

## PLIKI DO PRZECZYTANIA
- frontend/src/app/features/auth/
- frontend/src/app/shared/

## CO ZROBIĆ
1. Stwórz feature `verification` w `frontend/src/app/features/verification/`
2. Komponent `VerificationPageComponent` — routing `/panel/verify`, guard: rola Owner lub Employee
3. Dwa tryby wprowadzania kodu:
   - Skan QR: komponent z ngx-scanner-qrcode — po zeskanowaniu automatycznie wywołuje weryfikację
   - Ręczne wpisanie: pole tekstowe z przyciskiem „Weryfikuj" — format `XXXX-XXXX-XXXX`
4. Po weryfikacji (`POST /api/vouchers/verify`) wyświetl panel z detalami:
   - Nazwa vouchera, wartość, data ważności, status
   - Dane kupującego i odbiorcy
   - Duży przycisk „Zrealizuj voucher" z dialogiem potwierdzenia
5. Po realizacji (`POST /api/vouchers/redeem`) — komunikat sukcesu, reset formularza do stanu początkowego
6. Obsługa błędów: AlreadyUsed, Expired, InvalidCode — każdy z innym komunikatem i kolorem
7. Layout zoptymalizowany pod tablet/telefon (pracownik używa na urządzeniu mobilnym)
8. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add frontend/src/app/features/verification/
git commit -m "feat(vouchers-fe): verification view, qr scan, manual code, redeem"
git push
docker compose -f docker-compose.dev.yml up -d --build frontend


## DEFINICJA UKOŃCZENIA
- [x] Skan QR uruchamia weryfikację automatycznie
- [x] Ręczne wpisanie kodu działa
- [x] Szczegóły vouchera wyświetlają się po weryfikacji
- [x] Realizacja zmienia status i resetuje formularz
- [x] Błędy wyświetlają odpowiednie komunikaty
## _STATUS
- stan: completed
- ukończony: 2026-04-12 07:20:55
