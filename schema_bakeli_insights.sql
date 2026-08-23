-- ============================================================================
-- BAKELI INSIGHTS — Schéma PostgreSQL (v1)
-- Basé sur : cahier des charges (sections 2 à 5) + fichiers réels fournis
-- (Évaluation de satisfaction, Qualité du coaching, Disponibilité créneaux)
--
-- Principe directeur : un schéma GÉNÉRIQUE qui absorbe aussi bien les
-- formulaires internes (Google Forms) que les futurs flux réseaux sociaux
-- (LinkedIn, X, WhatsApp...), pour ne pas avoir à tout refaire à chaque
-- nouveau canal branché.
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- nécessaire pour gen_random_uuid()

-- ----------------------------------------------------------------------------
-- 1. UTILISATEURS DE LA PLATEFORME (Direction, Marketing, Pédagogie, Admin)
--    -> section 5.3 : Gouvernance des accès
-- ----------------------------------------------------------------------------
CREATE TABLE utilisateurs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT NOT NULL UNIQUE,
    nom_complet     TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('direction', 'marketing', 'pedagogie', 'admin')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE utilisateurs IS 'Comptes internes Bakeli. Le rôle détermine les données visibles (RLS à appliquer en Supabase).';

-- ----------------------------------------------------------------------------
-- 2. PLATEFORMES / CANAUX D'ÉCOUTE
--    -> section 2 : Réseaux publics, canaux privés, canaux internes
-- ----------------------------------------------------------------------------
CREATE TABLE plateformes (
    id              SERIAL PRIMARY KEY,
    code            TEXT NOT NULL UNIQUE,      -- ex: 'linkedin', 'whatsapp', 'google_forms'
    nom_affiche     TEXT NOT NULL,             -- ex: 'LinkedIn', 'WhatsApp', 'Google Forms'
    categorie       TEXT NOT NULL CHECK (categorie IN ('reseau_public', 'canal_prive', 'canal_interne')),
    actif           BOOLEAN NOT NULL DEFAULT true,
    connecte_depuis TIMESTAMPTZ
);

INSERT INTO plateformes (code, nom_affiche, categorie) VALUES
    ('linkedin',        'LinkedIn',              'reseau_public'),
    ('twitter_x',       'X (ex-Twitter)',        'reseau_public'),
    ('instagram',       'Instagram',             'reseau_public'),
    ('facebook',        'Facebook',              'reseau_public'),
    ('tiktok',          'TikTok',                'reseau_public'),
    ('google_business', 'Google My Business',    'reseau_public'),
    ('whatsapp',        'WhatsApp',              'canal_prive'),
    ('discord',         'Discord',               'canal_prive'),
    ('telegram',        'Telegram',              'canal_prive'),
    ('google_forms',    'Google Forms',          'canal_interne'),
    ('typeform',        'Typeform',              'canal_interne');

-- ----------------------------------------------------------------------------
-- 3. FORMULAIRES INTERNES (un par Google Form / Typeform importé)
-- ----------------------------------------------------------------------------
CREATE TABLE formulaires (
    id              SERIAL PRIMARY KEY,
    plateforme_id   INT NOT NULL REFERENCES plateformes(id),
    nom             TEXT NOT NULL,             -- ex: "Évaluation de satisfaction - Fin de formation"
    type_formulaire TEXT NOT NULL,             -- ex: 'satisfaction_fin_formation', 'qualite_coaching', 'disponibilite_creneaux'
    periode         TEXT,                      -- ex: 'Trimestre 1 2026'
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------------------------------------------------------
-- 4. IDENTITÉS TEMPORAIRES (PII brute, purge automatique)
--    -> section 5.1 et 5.2 : Anonymisation automatique, cycle de vie 90 jours
--    Cette table NE DOIT JAMAIS être exposée à l'API directement.
--    Un job planifié (cron / Edge Function) supprime les lignes expirées.
-- ----------------------------------------------------------------------------
CREATE TABLE identites_temporaires (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    apprenant_id    UUID NOT NULL,             -- référence vers apprenants.id
    prenom          TEXT,
    nom             TEXT,
    telephone       TEXT,
    email           TEXT,
    source_import   TEXT,                      -- d'où vient la donnée (nom du fichier, etc.)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at      TIMESTAMPTZ NOT NULL DEFAULT (now() + INTERVAL '90 days')
);
COMMENT ON TABLE identites_temporaires IS 'PII brute. Purge automatique après 90 jours (section 5.2 du cahier des charges).';

-- ----------------------------------------------------------------------------
-- 5. APPRENANTS (identité anonymisée et durable)
--    -> section 5.1 : jeton d'identification unique (ex: User_9841)
-- ----------------------------------------------------------------------------
CREATE TABLE apprenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_anonyme       TEXT NOT NULL UNIQUE,   -- généré à la création, ex: 'User_9841'
    domaine_formation   TEXT,                   -- 'Programmation', 'Marketing digital', 'Design', ...
    statut_pro          TEXT,                   -- 'Étudiant temps plein', 'Étudiant + emploi', 'Sans emploi'
    cohort              TEXT,                   -- promo / cohorte si connue
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE identites_temporaires
    ADD CONSTRAINT fk_identites_apprenant FOREIGN KEY (apprenant_id) REFERENCES apprenants(id);

-- ----------------------------------------------------------------------------
-- 6. THÉMATIQUES (Vue Opérationnelle / Équipe Pédagogique — section 4.B)
-- ----------------------------------------------------------------------------
CREATE TABLE thematiques (
    id              SERIAL PRIMARY KEY,
    nom             TEXT NOT NULL UNIQUE,       -- 'Le Rythme / Planning', 'La Plateforme / Outils', ...
    mots_cles       TEXT[] NOT NULL,            -- ['trop rapide','temps','horaires','fatiguant','charge']
    kpi_pilote      TEXT                        -- 'Taux de surcharge perçu', ...
);

INSERT INTO thematiques (nom, mots_cles, kpi_pilote) VALUES
    ('Le Rythme / Planning',    ARRAY['trop rapide','temps','horaires','fatiguant','charge'], 'Taux de surcharge perçu'),
    ('La Plateforme / Outils',  ARRAY['connexion','bug','site','vidéo','accès','serveur','zoom'], 'Taux d''incidents techniques'),
    ('La Pédagogie / Mentors',  ARRAY['coach','explications','clair','dispo','encadrement'], 'Note de performance mentors'),
    ('Le Contenu / Projets',    ARRAY['exercice','pratique','cours','projet','concret','atelier'], 'Indice de pertinence pratique');

-- ----------------------------------------------------------------------------
-- 7. AVIS (table centrale — un avis = un message/une réponse, quel que soit le canal)
--    -> section 3 : Traitement IA (sentiment, note, thématique, résumé)
--    -> section 4.C : Mur des plaintes (statut_moderation)
-- ----------------------------------------------------------------------------
CREATE TABLE avis (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    apprenant_id        UUID REFERENCES apprenants(id),       -- NULL si auteur externe non identifié (ex: post LinkedIn public)
    plateforme_id       INT NOT NULL REFERENCES plateformes(id),
    formulaire_id       INT REFERENCES formulaires(id),        -- NULL si ça ne vient pas d'un formulaire

    -- Contenu
    texte_brut          TEXT,                                  -- purgé après 90 jours si nominatif (job planifié)
    texte_brut_expires_at TIMESTAMPTZ,
    langue_detectee      TEXT,                                 -- 'fr', 'wo' (wolof), 'fr-wo' (mix/code-switching)

    -- Résultats du pipeline NLP (étape "Traitement IA")
    sentiment           TEXT CHECK (sentiment IN ('positif', 'neutre', 'negatif')),
    note                SMALLINT CHECK (note BETWEEN 1 AND 5),
    thematique_id        INT REFERENCES thematiques(id),
    resume               TEXT,

    -- Modération (Vue Alerte & Community Manager — section 4.C)
    statut_moderation    TEXT NOT NULL DEFAULT 'nouveau'
                          CHECK (statut_moderation IN ('nouveau', 'en_cours', 'traite')),
    traite_par            UUID REFERENCES utilisateurs(id),
    traite_at             TIMESTAMPTZ,

    -- Métadonnées brutes (flexible, garde tout ce qu'on n'a pas encore modélisé)
    raw_payload           JSONB,

    -- Traçabilité
    date_publication       TIMESTAMPTZ NOT NULL,   -- date réelle du post/de la réponse (horodateur du form, date du post...)
    date_ingestion          TIMESTAMPTZ NOT NULL DEFAULT now(),
    date_traitement_ia      TIMESTAMPTZ             -- rempli une fois le scoring IA effectué
);

CREATE INDEX idx_avis_plateforme ON avis(plateforme_id);
CREATE INDEX idx_avis_sentiment ON avis(sentiment);
CREATE INDEX idx_avis_thematique ON avis(thematique_id);
CREATE INDEX idx_avis_statut_moderation ON avis(statut_moderation) WHERE statut_moderation != 'traite';
CREATE INDEX idx_avis_date_publication ON avis(date_publication);

COMMENT ON COLUMN avis.texte_brut IS 'Contenu nominatif brut. À purger après 90 jours -- ne garder que le score agrégé (section 5.2).';

-- ----------------------------------------------------------------------------
-- 8. IMPORTS (historique des imports CSV/Excel — écran "Données" de l'app)
-- ----------------------------------------------------------------------------
CREATE TABLE imports (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    utilisateur_id      UUID REFERENCES utilisateurs(id),
    formulaire_id        INT REFERENCES formulaires(id),
    nom_fichier          TEXT NOT NULL,
    statut               TEXT NOT NULL DEFAULT 'en_cours' CHECK (statut IN ('en_cours', 'succes', 'echec', 'partiel')),
    lignes_totales        INT DEFAULT 0,
    lignes_importees      INT DEFAULT 0,
    lignes_en_erreur      INT DEFAULT 0,
    mapping_colonnes      JSONB,                 -- correspondance colonne fichier -> champ avis (étape "2. Mapping" de l'UI)
    erreurs_detail        JSONB,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    termine_at            TIMESTAMPTZ
);

-- ----------------------------------------------------------------------------
-- 9. VUES UTILES POUR LE DASHBOARD (section 4.A — Vue Macro / Direction)
-- ----------------------------------------------------------------------------

-- Index de Satisfaction Global (ISG) — moyenne pondérée sur 10
CREATE VIEW v_indice_satisfaction_global AS
SELECT
    ROUND(AVG(note)::numeric * 2, 1) AS isg_sur_10,  -- conversion note/5 -> /10
    COUNT(*) AS nb_avis
FROM avis
WHERE note IS NOT NULL
  AND date_publication >= now() - INTERVAL '7 days';

-- Répartition des sentiments (Thermomètre d'Humeur)
CREATE VIEW v_repartition_sentiments AS
SELECT
    sentiment,
    COUNT(*) AS nb,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pourcentage
FROM avis
WHERE sentiment IS NOT NULL
  AND date_publication >= now() - INTERVAL '7 days'
GROUP BY sentiment;

-- Mur des plaintes (Vue Alerte & Modération — section 4.C)
CREATE VIEW v_mur_des_plaintes AS
SELECT
    a.id, a.texte_brut, a.resume, a.thematique_id, t.nom AS thematique,
    a.date_publication, a.date_ingestion, a.statut_moderation, p.nom_affiche AS plateforme
FROM avis a
JOIN plateformes p ON p.id = a.plateforme_id
LEFT JOIN thematiques t ON t.id = a.thematique_id
WHERE a.sentiment = 'negatif'
  AND a.statut_moderation != 'traite'
ORDER BY a.date_publication DESC;

-- ============================================================================
-- NOTES D'IMPLÉMENTATION
-- ============================================================================
-- 1. Si déploiement sur Supabase : activer Row Level Security (RLS) sur
--    `avis`, `apprenants`, `identites_temporaires` en fonction de
--    utilisateurs.role (section 5.3 - Gouvernance des accès) :
--      - role='marketing'   -> plateformes.categorie = 'reseau_public' uniquement
--      - role='pedagogie'   -> plateformes.categorie = 'canal_interne' uniquement
--      - role='direction'   -> lecture agrégée uniquement (vues, pas la table avis brute)
--
-- 2. Job planifié à créer (pg_cron ou Supabase Edge Function + cron) :
--      DELETE FROM identites_temporaires WHERE expires_at < now();
--      UPDATE avis SET texte_brut = NULL WHERE texte_brut_expires_at < now();
--
-- 3. `raw_payload` (JSONB) sert de filet de sécurité : toute donnée du fichier
--    source qui n'a pas encore de colonne dédiée est conservée ici plutôt que
--    perdue, en attendant qu'on décide si elle mérite sa propre colonne.
-- ============================================================================
