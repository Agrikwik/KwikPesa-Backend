CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE TYPE account_type AS ENUM ('MERCHANT', 'TREASURY', 'FEE_COLLECTION', 'PROVIDER_SETTLEMENT');

-- 2. Create the unified table
CREATE TABLE ledger.users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'merchant',
    is_verified BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    business_name VARCHAR(255),
    business_phone VARCHAR(50),
    business_category VARCHAR(100),
    business_address TEXT,
    personal_phone VARCHAR(50),
    balance DECIMAL(20, 4) DEFAULT 0.0000,
    api_key_hashed VARCHAR(255) UNIQUE,
    secret_key_hashed VARCHAR(255),
    public_key VARCHAR(100) UNIQUE,
    webhook_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--  Accounts Table (The "Vaults")
CREATE TABLE ledger.accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    type account_type NOT NULL,
    currency CHAR(3) DEFAULT 'MWK',
    balance DECIMAL(20, 4) DEFAULT 0.0000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

--  Transactions Table
CREATE TABLE ledger.transactions (
    id VARCHAR(50) PRIMARY KEY,
    merchant_id UUID REFERENCES ledger.merchants(id),
    amount DECIMAL(20, 4) NOT NULL,
    provider VARCHAR(20),
    destination VARCHAR(50),
    status VARCHAR(20) DEFAULT 'PENDING',
    provider_reference VARCHAR(255),
    idempotency_key VARCHAR(255) UNIQUE,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

--  Ledger Entries
CREATE TABLE ledger.ledger_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id VARCHAR(50) NOT NULL REFERENCES ledger.transactions(id),
    account_id UUID NOT NULL,
    debit DECIMAL(20, 4) DEFAULT 0.0000,
    credit DECIMAL(20, 4) DEFAULT 0.0000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Payment Link (Digital Invoice) Table
CREATE TABLE ledger.payment_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    short_code VARCHAR(20) UNIQUE NOT NULL,
    merchant_id UUID REFERENCES ledger.merchants(id),
    amount DECIMAL(12, 2) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the OTPs table
CREATE TABLE ledger.otps (
    id UUID PRIMARY KEY,
    email VARCHAR NOT NULL,
    code VARCHAR(6) NOT NULL,
    purpose VARCHAR DEFAULT 'registration',
    expires_at TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE
);

-- Create the Products table
CREATE TABLE IF NOT EXISTS ledger.products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0,
    image_url TEXT, 
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);


--  Performance Indexes
CREATE INDEX idx_ledger_transaction_id ON ledger.ledger_entries(transaction_id);
CREATE INDEX idx_ledger_account_id ON ledger.ledger_entries(account_id);
CREATE INDEX idx_tx_merchant_id ON ledger.transactions(merchant_id);
CREATE INDEX idx_products_merchant ON ledger.products(merchant_id);