set search_path = wiki, public;

BEGIN;

alter table article add column bibtex_key_i citext;
alter table article add column bibtex_source_tmp text;
alter table article add column bibtex_html_tmp text;

UPDATE article SET bibtex_key_i = bibtex_key,
                   bibtex_source_tmp = bibtex_source,
                   bibtex_html_tmp = bibtex_html;

alter table article drop column bibtex_key cascade;
alter table article drop column bibtex_source cascade;
alter table article drop column bibtex_html cascade;

alter table article rename column bibtex_key_i to bibtex_key;
alter table article rename column bibtex_source_tmp to bibtex_source;
alter table article rename column bibtex_html_tmp to bibtex_html;

alter table article add constraint "article_bibtex_unique" unique(bibtex_key);

CREATE INDEX article_bibtex_key ON article(bibtex_key);

alter table article drop column tsvector;
alter table article add column titles_tsvector tsvector not null default to_tsvector('simple', '');
alter table article add column bibtex_tsvector tsvector not null default to_tsvector('simple', '');
alter table article add column main_tsvector tsvector not null default to_tsvector('simple', '');
alter table article add column tsvector tsvector generated always as (main_tsvector||titles_tsvector||bibtex_tsvector) stored;

CREATE INDEX article_fulltext ON article USING GIN (tsvector);



COMMIT;
