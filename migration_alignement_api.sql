-- Migration additive vers le modele utilise par l'API Bakeli Insights.
-- A executer dans pgAdmin sur la base existante.
-- Faire une sauvegarde de la base avant execution.

BEGIN;

-- Identites temporaires : le code Python utilise source_fichier.
ALTER TABLE identites_temporaires
    ADD COLUMN IF NOT EXISTS source_fichier TEXT;

UPDATE identites_temporaires
SET source_fichier = source_import
WHERE source_fichier IS NULL
  AND EXISTS (
      SELECT 1
      FROM information_schema.columns
      WHERE table_name = 'identites_temporaires'
        AND column_name = 'source_import'
  );

COMMIT;

-- Verification apres execution :
-- SELECT COUNT(*) AS identites_avec_source_fichier
-- FROM identites_temporaires WHERE source_fichier IS NOT NULL;
