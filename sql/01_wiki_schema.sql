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
    WITH english_hunspell, english_stem; -- pg_catalog.simple;


ALTER TEXT SEARCH CONFIGURATION  german
    ALTER MAPPING FOR asciiword, asciihword, hword_asciipart,
                      word, hword, hword_part
    WITH german_hunspell, pg_catalog.german_stem; -- pg_catalog.simple;


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

    ignore_namespace BOOLEAN NOT NULL DEFAULT false,
    
    root_language language NOT NULL,    
    source TEXT NOT NULL DEFAULT '',
    source_md5 CHAR(32) GENERATED ALWAYS AS (MD5(source)) STORED,
    format format NOT NULL,

    user_info_source TEXT NOT NULL DEFAULT '',

    bibtex_source TEXT,
    bibtex_key TEXT,

    current_html TEXT NOT NULL,
    user_info JSONB NOT NULL DEFAULT '{}'::JSONB,
    macro_info JSONB NOT NULL DEFAULT '{}'::JSONB,
    bibtex JSONB,

    teaser TEXT GENERATED ALWAYS AS (teaser_from_html(current_html)) STORED,
    
    tsvector tsvector NOT NULL DEFAULT to_tsvector('simple', ''),
    ctime TIMESTAMP NOT NULL DEFAULT NOW(),
    mtime TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TRIGGER update_mtime_on_article
   BEFORE INSERT OR UPDATE ON article FOR EACH ROW
   EXECUTE PROCEDURE update_mtime();

CREATE TABLE article_title
(
    article_id INTEGER NOT NULL REFERENCES article ON DELETE CASCADE,
    
    title citext NOT NULL,
    namespace citext,

    full_title citext GENERATED ALWAYS AS (
        CASE WHEN namespace IS NULL THEN title::text
             WHEN namespace IS NOT NULL THEN (
                 (title::text || ' ('::text) || namespace::text) || ')'::text
             ELSE NULL::text
        END::citext
    ) STORED,

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
