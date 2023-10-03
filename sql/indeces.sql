BEGIN;

set search_path = wiki, public;

CREATE INDEX article_fulltitle_index ON article_title(full_title);
CREATE INDEX article_bibtex_key ON article(bibtex_key);

CREATE INDEX article_fulltext ON article_rendition USING GIN (tsvector);

CREATE INDEX article_bibref_article_id ON article_bibref(article_id);
CREATE INDEX article_include_article_id ON article_include(article_id);
CREATE INDEX article_link_article_id ON article_link(article_id);
CREATE INDEX article_title_article_id ON article_title(article_id);


set search_path = archive, public;

CREATE INDEX article_revision_article_id ON article_revision(article_id);


set search_path = uploads, public;

CREATE INDEX upload_article_id ON upload(article_id);

COMMIT;
