-- Create access_tokens table
CREATE TABLE IF NOT EXISTS public.access_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token TEXT UNIQUE NOT NULL,
    category_name TEXT NOT NULL,
    label TEXT,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    revoked_at TIMESTAMPTZ,
    CONSTRAINT fk_category
        FOREIGN KEY (category_name)
        REFERENCES public.data_sources(category_name)
        ON DELETE CASCADE
);

-- Add category_name column to conversations table
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS category_name TEXT;
