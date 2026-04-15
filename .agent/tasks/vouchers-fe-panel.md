## ZADANIE
Stwórz widok listy i szczegółów voucherów w panelu właściciela.

## PLIKI DO PRZECZYTANIA
- frontend/src/app/features/orders/

## CO ZROBIĆ
1. Stwórz feature `vouchers` w `frontend/src/app/features/vouchers/`
2. Komponent `VoucherListComponent` — tabela z kolumnami: Kod, Typ vouchera, Kupujący, Wartość, Ważny do, Status, Akcje
3. Filtry: Status (dropdown), Data ważności od/do, Typ vouchera (dropdown)
4. Komponent `VoucherDetailComponent` — routing `/panel/vouchers/:id`:
   - Szczegóły: kod, QR code (renderowany w przeglądarce z biblioteki), wartość, data ważności, status, UsedAt
   - Dane zamówienia i kupującego
   - Link do pobrania PDF (jeśli PdfUrl dostępny)
5. Badge statusu: Active (zielony), Used (szary), Expired (czerwony)
6. Routing: `/panel/vouchers`
7. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add frontend/src/app/features/vouchers/
git commit -m "feat(vouchers-fe): voucher list, filters, detail with QR, pdf download"
git push
docker compose -f docker-compose.dev.yml up -d --build frontend


## DEFINICJA UKOŃCZENIA
- [x] Lista voucherów ładuje się z filtrami
- [x] Szczegóły vouchera wyświetlają QR code
- [x] Link do PDF działa
- [x] Statusy mają poprawne kolory
## _STATUS
- stan: completed
- ukończony: 2026-04-12 07:20:27
