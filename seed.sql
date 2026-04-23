-- Seed: planos iniciais do sistema
-- Executar após subir o banco: docker compose exec postgres psql -U postgres -d track_money_db -f /seed.sql

INSERT INTO subscription.plans (name, max_number_accounts, price, is_free, created_at)
VALUES
    ('Free Plan',    1,  0.00,  true,  NOW()),
    ('Basic Plan',   5,  9.90,  false, NOW()),
    ('Premium Plan', 15, 19.99, false, NOW())
ON CONFLICT (name) DO NOTHING;
