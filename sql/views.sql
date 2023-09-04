BEGIN;

set search_path = wiki, public;

DROP VIEW IF EXISTS article_info CASCADE;
CREATE VIEW article_info AS
   SELECT id, uuid,
          title AS main_title, namespace, root_language, format,
          ignore_namespace
     FROM article
     LEFT JOIN article_title ON article_id = article.id AND is_main_title;


DROP VIEW IF EXISTS article_for_view CASCADE;
CREATE VIEW article_for_view AS
    SELECT id, title AS main_title, namespace, root_language,
           current_html,
           user_info::TEXT, macro_info::TEXT           
      FROM article
      LEFT JOIN article_title ON article_id = article.id AND is_main_title;

DROP VIEW IF EXISTS article_fulltitle CASCADE;
CREATE VIEW article_fulltitle AS
    SELECT article_id, title, namespace, is_main_title, (
        CASE
          WHEN namespace IS NULL THEN title
          WHEN namespace IS NOT NULL THEN (
             (title || ' (') || namespace) || ')'
        END) as fulltitle
     FROM article_title;

DROP VIEW IF EXISTS article_main_title CASCADE;
CREATE VIEW article_main_title AS
    SELECT article_id, title, namespace, fulltitle, is_main_title
      FROM article_fulltitle;

DROP VIEW IF EXISTS article_namespace CASCADE;
CREATE VIEW article_namespace AS
    SELECT article_id, namespace
      FROM article_title
     WHERE is_main_title = true;

DROP VIEW IF EXISTS article_link_ranks CASCADE;
CREATE VIEW article_link_ranks AS 
    SELECT article_link.article_id,
           target_title AS target,
           article_fulltitle.fulltitle,
           CASE WHEN ans.namespace IS NOT NULL
                 AND article_fulltitle.namespace IS NOT NULL
                 AND ans.namespace = article_fulltitle.namespace
                THEN 4

                WHEN ans.namespace IS NULL
                 AND article_fulltitle.namespace IS NOT NULL
                THEN 3

                WHEN article_fulltitle.fulltitle = target_title
                THEN 2

                ELSE 1
           END AS rank            
      FROM article_link
      LEFT JOIN article_fulltitle
             ON article_fulltitle.title = target_title
             OR article_fulltitle.fulltitle = target_title
      LEFT JOIN article_namespace AS ans
             ON ans.article_id = article_link.article_id;

DROP VIEW IF EXISTS article_link_resolved CASCADE;
CREATE VIEW article_link_resolved AS
    SELECT article_id, target, fulltitle FROM article_link_ranks
     WHERE rank = (SELECT MAX(rank) FROM article_link_ranks AS inner_
                    WHERE inner_.article_id = article_link_ranks.article_id
                      AND inner_.target = article_link_ranks.target);



DROP VIEW IF EXISTS article_teaser CASCADE;
CREATE VIEW article_teaser AS
   SELECT article_id,
          REGEXP_REPLACE(SUBSTR(current_html, 0, 200),
                         '<[^>]*>|<[^>]*$', '', 'g') AS teaser,
          CASE WHEN LENGTH(current_html) > 200 THEN ' …'
               ELSE ''
          END AS elipsis
     FROM article
     LEFT JOIN article_title
            ON article_title.article_id = article.id
           AND article_title.is_main_title;          

DROP VIEW IF EXISTS article_teaser_on_resolved CASCADE;
CREATE VIEW article_teaser_on_resolved AS
SELECT article_teaser.article_id,
       article_link_resolved.fulltitle AS resolved_fulltitle,
       title AS main_title, namespace,
       teaser, elipsis
  FROM article_link_resolved
  LEFT JOIN article_teaser
    ON article_link_resolved.article_id = article_teaser.article_id
  LEFT JOIN article_title
    ON article_title.article_id = article_teaser.article_id
    AND is_main_title;
    
COMMIT;
