BEGIN;

CREATE TEXT SEARCH DICTIONARY english_hunspell (
    TEMPLATE  = ispell, DictFile = en_US,
    AffFile = en_US, Stopwords = english
);

CREATE TEXT SEARCH DICTIONARY german_hunspell (
    TEMPLATE  = ispell, DictFile = de_DE,
    AffFile = de_DE, Stopwords = german
);

ALTER TEXT SEARCH CONFIGURATION english
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart,
                      word, hword, hword_part
    WITH english_hunspell, pg_catalog.simple;


ALTER TEXT SEARCH CONFIGURATION german
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart,
                      word, hword, hword_part
    WITH german_hunspell, pg_catalog.simple;


set search_path = public;
CREATE EXTENSION IF NOT EXISTS citext;

DROP SCHEMA IF EXISTS wiki CASCADE;
CREATE SCHEMA wiki;

set search_path = wiki, public;

CREATE TYPE language AS ENUM ( 'en', 'de' );
CREATE TYPE format AS ENUM ( 'wikkly', 'wikitext', 'html' );

CREATE TABLE article
(
    id SERIAL PRIMARY KEY,
    uuid UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),

    ignore_namespace BOOLEAN NOT NULL DEFAULT false,
    
    root_language language NOT NULL,    
    source TEXT NOT NULL DEFAULT '',
    format format NOT NULL,
    current_html TEXT NOT NULL DEFAULT '',

    user_info_source TEXT NOT NULL DEFAULT '',
    user_info JSONB NOT NULL DEFAULT '{}'::JSONB,

    macro_info JSONB NOT NULL DEFAULT '{}'::JSONB,

    bibtex_source TEXT,
    bibtex_key TEXT,
    bibtex JSONB,

    tsvector tsvector NOT NULL DEFAULT to_tsvector('simple', ''),

    ctime TIMESTAMP NOT NULL DEFAULT NOW(),
    mtime TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TRIGGER update_mtime_on_article
   AFTER INSERT OR UPDATE ON article FOR EACH ROW
   EXECUTE PROCEDURE update_mtime();


CREATE TABLE article_title
(
    article_id INTEGER NOT NULL REFERENCES article ON DELETE CASCADE,
    title citext NOT NULL,
    namespace citext,
    language language NOT NULL,
    is_main_title BOOLEAN NOT NULL,

    UNIQUE (title, namespace)
);

CREATE TABLE article_link
(
    article_id INTEGER NOT NULL REFERENCES article ON DELETE CASCADE,
    target_title citext NOT NULL, -- Maybe including namespace

    UNIQUE(article_id, target_title)
);

CREATE TABLE article_include
(
    article_id INTEGER NOT NULL REFERENCES article ON DELETE CASCADE,
    wants_to_include citext NOT NULL, -- Maybe including namespace
    
    UNIQUE(article_id, wants_to_include)
);

CREATE TABLE article_bibref
(
    article_id INTEGER NOT NULL REFERENCES article ON DELETE CASCADE,
    citekey citext NOT NULL,    
    UNIQUE(article_id, citekey)
);

COMMIT;
