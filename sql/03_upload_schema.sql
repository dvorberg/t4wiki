BEGIN;

DROP SCHEMA IF EXISTS uploads CASCADE;
CREATE SCHEMA uploads;

set search_path = uploads, wiki, public;

CREATE TABLE upload
(
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES article ON DELETE CASCADE,
    filename TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    gallery BOOLEAN NOT NULL DEFAULT false,
    download BOOLEAN NOT NULL DEFAULT false,
    sortrank FLOAT NOT NULL DEFAULT 0.0,
    width INTEGER,
    height INTEGER,
    data BYTEA NOT NULL,
    url TEXT,
    ctime TIMESTAMP NOT NULL DEFAULT NOW(),
    slug CHAR(20) NOT NULL DEFAULT slug(),

    UNIQUE(article_id, filename),
    UNIQUE(slug)
);

COMMIT;
