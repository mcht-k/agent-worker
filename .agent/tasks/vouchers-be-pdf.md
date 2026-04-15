## ZADANIE
Zaimplementuj generowanie PDF vouchera przez QuestPDF z 3 szablonami i uploadem do storage.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Vouchers/
- backend/Vouchify.Infrastructure/

## CO ZROBIĆ
1. Stwórz interfejs `IVoucherPdfGenerator` z metodą `GenerateAsync(VoucherPdfData data) → byte[]`
2. Zaimplementuj `QuestPdfVoucherGenerator` — stwórz 3 szablony (TemplateId 1–3):
   - Szablon 1: klasyczny — logo góra, kod środek, QR dół
   - Szablon 2: nowoczesny — gradient tło, kod w ramce
   - Szablon 3: minimalistyczny — tylko tekst, kod i QR
   - Każdy szablon respektuje PdfConfig (ShowAmount, ShowDescription, ShowQrCode, ShowLink, ShowExpiryDate)
3. Stwórz interfejs `IVoucherStorage` z metodą `SaveAsync(voucherId, bytes) → string url`
4. Implementacja `LocalVoucherStorage` — zapisuje do `wwwroot/vouchers/{tenantId}/{voucherId}.pdf` — zwraca publiczny URL
5. Handler dla eventu `VoucherCreated`:
   - Generuje PDF
   - Zapisuje przez IVoucherStorage
   - Aktualizuje Voucher.PdfUrl
   - Publikuje event `VoucherPdfGenerated`
6. Dodaj pole `PdfUrl` (nullable string) do encji Voucher + migracja `AddVoucherPdfUrl`
7. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Vouchers/ backend/Vouchify.Infrastructure/
git commit -m "feat(vouchers): pdf generation questpdf 3 templates, local storage"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] PDF generuje się po utworzeniu vouchera
- [x] 3 szablony renderują się bez błędów
- [x] Pola widoczności z PdfConfig są respektowane
- [x] PdfUrl zapisany w bazie po wygenerowaniu
## _STATUS
- stan: completed
- ukończony: 2026-04-12 01:19:24
