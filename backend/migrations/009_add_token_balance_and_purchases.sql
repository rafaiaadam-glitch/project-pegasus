-- Token balance columns on users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS free_token_balance INTEGER NOT NULL DEFAULT 100000;
ALTER TABLE users ADD COLUMN IF NOT EXISTS purchased_token_balance INTEGER NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS free_tokens_reset_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Token transactions (append-only audit log for all balance changes)
CREATE TABLE IF NOT EXISTS token_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    transaction_type TEXT NOT NULL,
    token_amount INTEGER NOT NULL,
    balance_after_free INTEGER NOT NULL,
    balance_after_purchased INTEGER NOT NULL,
    reference_id TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_token_txn_user ON token_transactions(user_id);

-- Purchase receipts (for IAP receipt validation + idempotency)
CREATE TABLE IF NOT EXISTS purchase_receipts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    platform TEXT NOT NULL,
    product_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL UNIQUE,
    receipt_data TEXT NOT NULL,
    tokens_granted INTEGER NOT NULL,
    price_usd REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'completed',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_purchase_user ON purchase_receipts(user_id);
