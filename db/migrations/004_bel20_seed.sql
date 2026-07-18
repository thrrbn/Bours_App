-- ============================================================================
-- Migration 004 : seed des 20 composants de l'indice BEL 20 (Euronext Bruxelles)
-- Composition verifiee via Euronext + EasyBourse en juillet 2026 - a corriger
-- toi-meme si la composition de l'indice change (revue annuelle en mars).
-- Tickers au format yfinance (suffixe .BR = cotation Euronext Bruxelles).
-- ON CONFLICT DO NOTHING : ne duplique pas Solvay, deja present en base.
--
-- A appliquer sur la base existante :
--   Get-Content db/migrations/004_bel20_seed.sql | docker compose exec -T db psql -U bourse_user -d bourse
-- ============================================================================

INSERT INTO assets (id, ticker, name, market, sector, currency, isin, is_active)
VALUES
    (uuid_generate_v4(), 'ACKB.BR',  'Ackermans & van Haaren', 'EURONEXT_BRUSSELS', 'Holding financier',            'EUR', 'BE0003764785', TRUE),
    (uuid_generate_v4(), 'AED.BR',   'Aedifica',               'EURONEXT_BRUSSELS', 'Immobilier sante (REIT)',      'EUR', 'BE0003851681', TRUE),
    (uuid_generate_v4(), 'AGS.BR',   'Ageas',                  'EURONEXT_BRUSSELS', 'Assurance',                    'EUR', 'BE0974264930', TRUE),
    (uuid_generate_v4(), 'ABI.BR',   'AB InBev',               'EURONEXT_BRUSSELS', 'Boissons',                     'EUR', 'BE0974293251', TRUE),
    (uuid_generate_v4(), 'APAM.BR',  'Aperam',                 'EURONEXT_BRUSSELS', 'Aciers speciaux',              'EUR', 'LU0569974404', TRUE),
    (uuid_generate_v4(), 'ARGX.BR',  'argenx',                 'EURONEXT_BRUSSELS', 'Biotechnologie',               'EUR', 'NL0010832176', TRUE),
    (uuid_generate_v4(), 'AZE.BR',   'Azelis Group',           'EURONEXT_BRUSSELS', 'Distribution chimique',        'EUR', 'BE0974400328', TRUE),
    (uuid_generate_v4(), 'DIE.BR',   'D''Ieteren Group',       'EURONEXT_BRUSSELS', 'Distribution automobile',      'EUR', 'BE0974259880', TRUE),
    (uuid_generate_v4(), 'ELI.BR',   'Elia Group',             'EURONEXT_BRUSSELS', 'Reseaux electriques',          'EUR', 'BE0003822393', TRUE),
    (uuid_generate_v4(), 'GBLB.BR',  'GBL',                    'EURONEXT_BRUSSELS', 'Holding financier',            'EUR', 'BE0003797140', TRUE),
    (uuid_generate_v4(), 'KBC.BR',   'KBC Group',              'EURONEXT_BRUSSELS', 'Banque',                       'EUR', 'BE0003565737', TRUE),
    (uuid_generate_v4(), 'LOTB.BR',  'Lotus Bakeries',         'EURONEXT_BRUSSELS', 'Agroalimentaire',              'EUR', 'BE0003604155', TRUE),
    (uuid_generate_v4(), 'MELE.BR',  'Melexis',                'EURONEXT_BRUSSELS', 'Semi-conducteurs',             'EUR', 'BE0165385973', TRUE),
    (uuid_generate_v4(), 'MONT.BR',  'Montea',                 'EURONEXT_BRUSSELS', 'Immobilier logistique (REIT)', 'EUR', 'BE0003853703', TRUE),
    (uuid_generate_v4(), 'SOF.BR',   'Sofina',                 'EURONEXT_BRUSSELS', 'Holding financier',            'EUR', 'BE0003717312', TRUE),
    (uuid_generate_v4(), 'SOLB.BR',  'Solvay',                 'EURONEXT_BRUSSELS', 'Chimie',                       'EUR', 'BE0003470755', TRUE),
    (uuid_generate_v4(), 'SYENS.BR', 'Syensqo',                'EURONEXT_BRUSSELS', 'Chimie de specialite',         'EUR', 'BE0974464977', TRUE),
    (uuid_generate_v4(), 'UCB.BR',   'UCB',                    'EURONEXT_BRUSSELS', 'Pharmaceutique',               'EUR', 'BE0003739530', TRUE),
    (uuid_generate_v4(), 'UMI.BR',   'Umicore',                'EURONEXT_BRUSSELS', 'Chimie / materiaux',           'EUR', 'BE0974320526', TRUE),
    (uuid_generate_v4(), 'WDP.BR',   'WDP',                    'EURONEXT_BRUSSELS', 'Immobilier logistique (REIT)', 'EUR', 'BE0974349814', TRUE)
ON CONFLICT (ticker, market) DO NOTHING;
