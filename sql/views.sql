BEGIN;

set search_path = wiki, public;

DROP VIEW IF EXISTS article_info CASCADE;
CREATE VIEW article_info AS
   SELECT id, uuid,
          title AS main_title, namespace, 
          ignore_namespace, format
     FROM article
     LEFT JOIN article_title ON article_id = article.id AND is_main_title;

COMMIT;
