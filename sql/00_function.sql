BEGIN;

set search_path = public;

CREATE OR REPLACE FUNCTION plpython3_call_handler()
   RETURNS language_handler AS '$libdir/plpython3.so' LANGUAGE 'c';

CREATE OR REPLACE LANGUAGE 'plpython' HANDLER plpython3_call_handler;



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



COMMIT;
