BEGIN;

CREATE UNIQUE INDEX article_fulltitle_index ON wiki.article_title ((
      CASE WHEN namespace IS NULL THEN title
           WHEN namespace IS NOT NULL THEN title || ' (' || namespace || ')'
      END    
));

COMMIT;
