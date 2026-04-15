## ZADANIE
Zaimplementuj flow zakupu przez Stripe Checkout: inicjowanie sesji, webhook potwierdzenia, zwroty i endpointy panelu.

## PLIKI DO PRZECZYTANIA
- backend/Modules/Vouchify.Modules.Orders/
- backend/Modules/Vouchify.Modules.Tenants/

## CO ZROBIĆ
1. Command `CreateCheckoutSessionCommand` (VoucherTypeId, Amount, BuyerEmail, BuyerName, RecipientEmail, RecipientName):
   - Waliduje VoucherType (istnieje, IsVisible, tenant Active)
   - Tworzy Order ze statusem Pending
   - Wywołuje Stripe `SessionService.CreateAsync` z `application_fee_amount` (prowizja platformy z AppSettings), `transfer_data.destination` = StripeAccountId tenanta
   - Zwraca `{ orderId, checkoutUrl }`
2. Endpoint publiczny `POST /t/{slug}/orders/checkout` (bez JWT)
3. Webhook `POST /api/webhooks/stripe/payments` — obsługuje:
   - `checkout.session.completed` → Order.Status = Paid, publikuje event `OrderPaid`
   - `payment_intent.payment_failed` → Order.Status = Failed
4. Idempotentność webhooków: tabela `ProcessedStripeEvents` (EventId, ProcessedAt) — pomiń jeśli EventId już istnieje
5. Command `RefundOrderCommand` (OrderId) → Stripe `RefundService.CreateAsync` → Order.Status = Refunded
6. Endpoint panelu `POST /api/orders/{id}/refund` — wymaga roli Owner
7. Query + endpoint panelu `GET /api/orders` — filtrowanie po Status, DateFrom, DateTo, VoucherTypeId — wymaga roli Owner
8. Endpoint `GET /api/orders/{id}` — szczegóły zamówienia
9. Po zakończeniu wszystkich kroków — zaznacz wszystkie checkboxy w sekcji ## DEFINICJA UKOŃCZENIA w tym pliku na [x]

## PO WYKONANIU

cd ~/projects/vouchify-mono
git add backend/Modules/Vouchify.Modules.Orders/ backend/Vouchify.Infrastructure/
git commit -m "feat(orders): stripe checkout, webhooks, refunds, panel endpoints"
git push
docker compose -f docker-compose.dev.yml up -d --build api


## DEFINICJA UKOŃCZENIA
- [x] `POST /t/{slug}/orders/checkout` zwraca URL Stripe Checkout
- [x] Webhook `checkout.session.completed` zmienia status na Paid
- [x] Tabela ProcessedStripeEvents deduplikuje eventy
- [x] Zwrot działa przez panel
- [x] Lista zamówień z filtrami działa
## _STATUS
- stan: completed
- ukończony: 2026-04-11 20:21:14
