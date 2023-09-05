BEGIN;

DROP SCHEMA IF EXISTS archive CASCADE;
CREATE SCHEMA archive;

set search_path = archive, wiki, public;

CREATE TABLE article_revision
(
    article_id INTEGER NOT NULL, -- No foreign key constraint.
                                 -- Allow article deletion. 
    full_title TEXT NOT NULL, 
    root_language language NOT NULL,
    format format NOT NULL,
    source TEXT NOT NULL,
    user_info_source TEXT,
    bibtex_source TEXT,
    ctime TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE (article_id, ctime)
);

COMMIT;
