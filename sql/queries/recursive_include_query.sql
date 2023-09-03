set search_path = wiki, public;

CREATE TEMPORARY VIEW includes AS 
    SELECT article_include.article_id AS includer,
           article_title.article_id AS included,
           wants_to_include
      FROM article_include
      LEFT JOIN article_title
        ON wants_to_include = (CASE WHEN namespace IS NULL THEN title
                                    WHEN namespace IS NOT NULL
                                        THEN title || ' (' || namespace || ')'
                                END)
     WHERE article_title.article_id IS NOT NULL;
     
WITH RECURSIVE rincludes(includer, included, wants_to_include) AS (
    SELECT includer, included, wants_to_include
      FROM includes
     WHERE includer = %s -- root article id
  UNION
    SELECT i.includer, i.included, i.wants_to_include
      FROM rincludes ri, includes i
     WHERE i.includer = ri.included
)
SELECT included AS article_id,
       wants_to_include AS included_as
  FROM rincludes
  LEFT JOIN article_info ON included = article_info.id
  GROUP BY included, included_as;

