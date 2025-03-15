BEGIN;

set search_path = wiki, public;

DROP VIEW IF EXISTS article_for_view CASCADE;
CREATE VIEW article_for_view AS
    SELECT id, title AS main_title, namespace, root_language, bibtex_key,
           current_html, bibtex_html, user_info::TEXT, macro_info::TEXT
      FROM article
      LEFT JOIN article_title
             ON article_title.article_id = article.id AND is_main_title;

DROP VIEW IF EXISTS article_for_redo CASCADE;
CREATE VIEW article_for_redo AS
    SELECT full_title, id, ignore_namespace, root_language, 
           source, format, user_info_source, 
           ( SELECT json_agg(json_build_object('lang', language,
                                               'title', title,
                                               'namespace', namespace))
               FROM article_title
              WHERE article_id = article.id ) AS titles
      FROM article
 LEFT JOIN article_title ON article_id = id AND is_main_title;

DROP VIEW IF EXISTS article_for_bibtex_redo CASCADE;
CREATE VIEW article_for_bibtex_redo AS
    SELECT full_title, id, bibtex_source, root_language
      FROM article
 LEFT JOIN article_title ON article_id = id AND is_main_title;


DROP VIEW IF EXISTS article_for_recent_changes_list CASCADE;
DROP VIEW IF EXISTS article_for_list CASCADE;
CREATE VIEW article_for_list AS
    SELECT id, title AS main_title, namespace, bibtex_key, teaser, mtime
      FROM article
      LEFT JOIN article_title ON article_id = id and is_main_title;

DROP VIEW IF EXISTS article_namespace CASCADE;
CREATE VIEW article_namespace AS
    SELECT article_id, namespace
      FROM article_title
     WHERE is_main_title = true;

DROP VIEW IF EXISTS article_info CASCADE;
CREATE VIEW article_info AS
   SELECT id, title AS main_title, namespace, ignore_namespace, root_language,
          format
     FROM article
LEFT JOIN article_title
       ON article_title.article_id = article.id AND is_main_title;

DROP VIEW IF EXISTS article_link_ranks CASCADE;
CREATE VIEW article_link_ranks AS 
    SELECT article_link.article_id,
           target_title AS target,
           full_title,
           CASE WHEN source_article.namespace IS NOT NULL
                 AND article_title.namespace IS NOT NULL
                 AND source_article.namespace = article_title.namespace
                THEN 4

                WHEN source_article.namespace IS NULL
                 AND article_title.namespace IS NOT NULL
                THEN 3

                WHEN article_title.full_title = target_title
                THEN 2

                ELSE 1
           END AS rank
      FROM article_link
      LEFT JOIN article_title
             ON article_title.title = target_title
                 OR article_title.full_title = target_title
      LEFT JOIN article_namespace AS source_article
             ON source_article.article_id = article_link.article_id;

DROP VIEW IF EXISTS article_link_resolved CASCADE;
CREATE VIEW article_link_resolved AS
    SELECT article_id, target, full_title
      FROM article_link_ranks
     WHERE rank = ( SELECT MAX(rank) FROM article_link_ranks AS inner_
                     WHERE inner_.article_id = article_link_ranks.article_id
                       AND inner_.target = article_link_ranks.target );

DROP VIEW IF EXISTS article_teaser_on_resolved CASCADE;
CREATE VIEW article_teaser_on_resolved AS
    SELECT article_link_resolved.article_id,
           article_link_resolved.full_title AS resolved_full_title,
           article_title.title AS main_title,
           article_title.namespace,
           teaser
      FROM article_link_resolved
 LEFT JOIN article_title
        ON article_title.article_id = article_link_resolved.article_id
            AND is_main_title
 LEFT JOIN article ON id = article_link_resolved.article_id;

DROP VIEW IF EXISTS current_article_revision CASCADE;
CREATE VIEW current_article_revision AS
    SELECT id,
           full_title,
           root_language,
           format,
           source,
           user_info_source,
           bibtex_source,
           NOW()
      FROM article
      LEFT JOIN article_title
           ON article_title.article_id = id AND is_main_title;


-- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 

set search_path = uploads, public;

DROP VIEW IF EXISTS upload_info CASCADE;
CREATE VIEW upload_info AS
   SELECT id, article_id, filename, title, description, gallery,
          is_download, sortrank, width, height, ctime, slug,
          substring(filename, '(\.[^\.]+$)') AS ext,
          CASE WHEN  substring(filename, '(\.[^\.]+$)') = '.png' THEN '.png'
               ELSE '.jpg'
          END AS preview_ext,
          length(data) AS size
     FROM upload;

DROP VIEW IF EXISTS upload_info_for_view CASCADE;
CREATE VIEW upload_info_for_view AS
WITH
upload_info_by_filename AS (
    SELECT article_id,
           filename,
           jsonb_build_object('id', id,
                              'slug', slug,
                              'pext', preview_ext,
                              'w', width,
                              'h', height,
                              'size', size,
                              'n', filename,
                              't', title,
                              'dl', is_download,
                              'g', gallery, 
                              'd', description) AS upload_info
      FROM upload_info
)
SELECT article_id, json_object_agg(filename, upload_info) AS uploads_info
  FROM upload_info_by_filename
 GROUP BY article_id;


COMMIT;
