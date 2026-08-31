-- Ajoute les résultats du pipeline NLP à la table avis existante.
BEGIN;

ALTER TABLE avis
    ADD COLUMN IF NOT EXISTS sentiment TEXT,
    ADD COLUMN IF NOT EXISTS note SMALLINT,
    ADD COLUMN IF NOT EXISTS resume TEXT,
    ADD COLUMN IF NOT EXISTS langue_detectee TEXT,
    ADD COLUMN IF NOT EXISTS date_traitement_ia TIMESTAMPTZ;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'avis_note_range'
    ) THEN
        ALTER TABLE avis ADD CONSTRAINT avis_note_range
            CHECK (note IS NULL OR note BETWEEN 1 AND 5);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_avis_sentiment ON avis(sentiment);
CREATE INDEX IF NOT EXISTS idx_avis_note ON avis(note);

COMMIT;
