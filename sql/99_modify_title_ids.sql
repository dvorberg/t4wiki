BEGIN;

ALTER TABLE wiki.article_title
  ADD COLUMN cmpid TEXT GENERATED ALWAYS
   AS (title_to_cmpid(title)) STORED;

ALTER TABLE wiki.article_title
  ADD COLUMN full_cmpid TEXT GENERATED ALWAYS
   AS ( CASE WHEN namespace IS NULL THEN title_to_cmpid(title)
             WHEN namespace IS NOT NULL THEN (
                 (title_to_cmpid(title)
                   || '_'::text)
                   || title_to_cmpid(namespace))
             ELSE NULL::text
        END::citext
    ) STORED;



ALTER TABLE wiki.article_link
  ADD COLUMN target_cmpid TEXT GENERATED ALWAYS
   AS (title_to_cmpid(target_title)) STORED;

COMMIT;
