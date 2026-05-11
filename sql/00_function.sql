BEGIN;

set search_path = public;

CREATE OR REPLACE FUNCTION plpython3_call_handler()
   RETURNS language_handler AS '$libdir/plpython3.so' LANGUAGE 'c';

-- CREATE OR REPLACE LANGUAGE 'plpython' HANDLER plpython3_call_handler;


CREATE OR REPLACE FUNCTION public.update_mtime() RETURNS trigger AS'
BEGIN
  /* Funktion liefert aktuellen Timestamp fuer Feld modification_time */
  NEW.mtime := now();
  RETURN NEW;
END;
' LANGUAGE 'plpgsql'; 


CREATE OR REPLACE FUNCTION slug() RETURNS TEXT 
AS $$
from t4.passwords import slug
return slug(20)
$$ LANGUAGE plpython;


CREATE OR REPLACE FUNCTION title_to_cmpid(title TEXT) RETURNS TEXT IMMUTABLE 
AS $$
from t4.title_to_id import title_to_id
return title_to_id(title)
$$ LANGUAGE plpython;


CREATE OR REPLACE FUNCTION html_wordcount(html TEXT) RETURNS INTEGER IMMUTABLE
AS $$
import re

br_re = re.compile(r"<br[^>]*>")
tag_re = re.compile(r"<[^>]+>")
whitespace_re = re.compile(r"\s+")

def wordcount(html:str|None) -> int:
    if html is None:
        return 0
        
    html = html.strip()

    if not html:
        return 0

    html = br_re.sub(" ", html)
    html = tag_re.sub("", html)
    return len(whitespace_re.split(html))

return wordcount(html)
$$ LANGUAGE plpython;


COMMIT;
