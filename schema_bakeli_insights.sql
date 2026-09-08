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
    source_fichier  TEXT,                      -- d'où vient la donnée (nom du fichier, etc.)
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
    cle             TEXT NOT NULL UNIQUE,       -- 'plateforme', 'technique', 'coach', ...
    nom_affiche     TEXT NOT NULL,
    mots_cles_regex TEXT
);

INSERT INTO thematiques (cle, nom_affiche, mots_cles_regex) VALUES
    ('plateforme', 'La Plateforme / Outils', 'platefor|plateform|platform|connexion|login|compte|site'),
    ('technique', 'Technique / Réseau', 'wifi|bug|technique|ordinateur|machine|réseau|reseau|panne|électric|electric'),
    ('coach', 'Coach / Formateur', 'coach|formateur|encadr|prof'),
    ('planning', 'Rythme / Planning', 'rythme|horaire|planning|retard|temps|durée|duree|vendredi'),
    ('projets', 'Projets / Exercices', 'projet|exercice|pratique|tp'),
    ('administration', 'Administration', 'administra|inscription|paiement|frais|attestation|certificat'),
    ('pedagogie', 'Pédagogie / Contenu', 'cours|théori|theori|contenu|apprentissage|module|niveau|pédagog|pedagog');

-- ----------------------------------------------------------------------------
-- 7. AVIS (table centrale — un avis = un message/une réponse, quel que soit le canal)
--    -> section 3 : Traitement IA (sentiment, note, thématique, résumé)
--    -> section 4.C : Mur des plaintes (statut_moderation)
-- ----------------------------------------------------------------------------
CREATE TABLE avis (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    apprenant_id         UUID REFERENCES apprenants(id),
    feedback_id          TEXT NOT NULL UNIQUE,
    date_avis            TIMESTAMPTZ,
    annee                INT,
    mois                 INT,
    plateforme_id        INT NOT NULL REFERENCES plateformes(id),
    campus               TEXT,
    promotion            TEXT,
    formation            TEXT,
    coach                TEXT,
    satisfaction_qualitative TEXT,
    satisfaction_score_10 SMALLINT CHECK (satisfaction_score_10 BETWEEN 0 AND 10),
    frequence_feedback  TEXT,
    source_feedback     TEXT,
    attentes_formation  TEXT,
    attentes_remplies   TEXT,
    besoin_cours_theorique TEXT,
    points_amelioration TEXT,
    avis_activites_vendredi TEXT,
    regroupement_niveaux TEXT,
    commentaire_libre   TEXT,
    langue              TEXT,
    texte_a_analyser_ia TEXT,
    sentiment           TEXT,
    note                SMALLINT CHECK (note IS NULL OR note BETWEEN 1 AND 5),
    resume              TEXT,
    langue_detectee     TEXT,
    date_traitement_ia  TIMESTAMPTZ,
    thematique_id       INT REFERENCES thematiques(id),
    statut_moderation   TEXT NOT NULL DEFAULT 'nouveau'
                         CHECK (statut_moderation IN ('nouveau', 'en_cours', 'traite')),
    source_fichier      TEXT,
    date_ingestion      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_avis_plateforme ON avis(plateforme_id);
CREATE INDEX idx_avis_thematique ON avis(thematique_id);
CREATE INDEX idx_avis_statut_moderation ON avis(statut_moderation) WHERE statut_moderation != 'traite';
CREATE INDEX idx_avis_date_avis ON avis(date_avis);

COMMENT ON COLUMN avis.texte_a_analyser_ia IS 'Texte conservé pour le pipeline d''analyse et la classification thématique.';

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
        ROUND(AVG(satisfaction_score_10)::numeric, 1) AS isg_sur_10,
    COUNT(*) AS nb_avis
FROM avis
WHERE satisfaction_score_10 IS NOT NULL
    AND date_avis >= now() - INTERVAL '7 days';

-- Répartition des sentiments (Thermomètre d'Humeur)
CREATE VIEW v_repartition_sentiments AS
SELECT
        CASE
                WHEN satisfaction_score_10 >= 8 THEN 'positif'
                WHEN satisfaction_score_10 <= 4 THEN 'negatif'
                ELSE 'neutre'
        END AS sentiment,
    COUNT(*) AS nb,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pourcentage
FROM avis
WHERE satisfaction_score_10 IS NOT NULL
    AND date_avis >= now() - INTERVAL '7 days'
GROUP BY 1;

-- Mur des plaintes (Vue Alerte & Modération — section 4.C)
CREATE VIEW v_mur_des_plaintes AS
SELECT
        a.id, a.commentaire_libre AS texte, a.texte_a_analyser_ia,
        a.thematique_id, t.nom_affiche AS thematique,
        a.date_avis, a.date_ingestion, a.statut_moderation, p.nom_affiche AS plateforme
FROM avis a
JOIN plateformes p ON p.id = a.plateforme_id
LEFT JOIN thematiques t ON t.id = a.thematique_id
WHERE a.satisfaction_score_10 <= 4
  AND a.statut_moderation != 'traite'
ORDER BY a.date_avis DESC;

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
--      -- Les données nominatives sont isolées dans identites_temporaires.
--
-- 3. Les champs du formulaire non reconnus par le mapping sont actuellement
--    ignorés; un champ JSONB pourra être ajouté lors d'une prochaine version.
-- ============================================================================
