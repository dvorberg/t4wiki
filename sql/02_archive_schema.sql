BEGIN;

DROP SCHEMA IF EXISTS archive CASCADE;
CREATE SCHEMA archive;

set search_path = archive, wiki, public;

CREATE TABLE article_revision
(
    article_id INTEGER NOT NULL REFERENCES article, 
    main_title_and_namespace TEXT NOT NULL, 
    language language NOT NULL,
    source_z BYTEA NOT NULL,
    format article_format NOT NULL,
    ctime TIMESTAMP NOT NULL DEFAULT NOW
);

COMMIT;
