# This will create a fake flask environmeht for my scripts to work in.
# I’m sure there are more elegant ways to do this, but I don’t have time
# to figure them out right now.

import os, os.path as op, getpass, select, time, threading, logging, json
import runpy
import psycopg2

from t4 import sql

config_file = os.getenv("YOURAPPLICATION_SETTINGS",
                        os.getenv("BLGD_APPLICATION_SETTINGS", None))
if config_file is None:
    raise IOError("YOURAPPLICATION_SETTINGS not set.")
elif not op.exists(config_file):
    raise IOError("Can’t read config from " + config_file)

config = runpy.run_path(config_file)

class Worker:
    def __init__(self):
        self._dbconn = None

    @property
    def dbconn(self):
        if self._dbconn is None:
            self._dbconn = psycopg2.connect(**config["DATASOURCE"])
        return self._dbconn

    def cursor(self):
        return self.dbconn.cursor()

class NotificationWorker(Worker):
    def __init__(self):
        super().__init__()
        self.timer = None

    @property
    def dbconn(self):
        ret = super().dbconn

        cursor = ret.cursor()
        logging.info("Starting to LISTEN to %s" % self.event_name)
        cursor.execute("LISTEN %s;" % self.event_name)
        ret.commit()

        return ret

    @property
    def event_name(self):
        raise NotImplementedError()

    @property
    def on_notification(self):
        raise NotImplementedError()

    def run(self):
        while True:
            try:
                self.dbconn.rollback()

                if select.select([self.dbconn], [], [], 1800) == ([],[],[]):
                    self.dbconn.rollback()
                else:
                    self.dbconn.poll()
                    work_needed = False
                    while self.dbconn.notifies:
                        notify = self.dbconn.notifies.pop()

                        if type(notify) == tuple:
                            pid, dummy = notify
                        else:
                            pid = notify.pid

                        if pid != self.dbconn.get_backend_pid():
                            work_needed = True

                    if work_needed:
                        try:
                            self.on_notification()
                        except Exception as e:
                            logger.info("Exception in work: " + repr(e))

            except ( psycopg2.DatabaseError,
                     psycopg2.OperationalError) as e:
                self.log_traceback()
                self._dbconn = None
                time.sleep(60)


class FakeGlobal(Worker):
    # FakeGlobal inherits from Worker, because
    # it has db connection management.

    debug_sql = True

    def __contains__(self, name):
        return hasattr(self, name)

    @property
    def config(self):
        return config



# Import flask
import flask

# Overwrite flask’s Global with ourselves. db.get_dbconn() will now
# find a dbconn in g and return it.
flask.g = FakeGlobal()
flask.current_app = flask.g

# Fake a session by loading my youngest session from the database.
# Yes. My login is hardwired here. Why not?
flask.session = dict()

# ds = flask.g.dbconn
# cursor = ds.cursor()
# cursor.execute("""SELECT name, value, is_string FROM session_fields
#                    WHERE session_id = ( SELECT session_id
#                                           FROM session_fields
#                                          WHERE name = 'user_login'
#                                            AND value = 'diedrich'
#                                           ORDER BY mtime DESC LIMIT 1 )""")
# for name, value, is_string in cursor.fetchall():
#     if not is_string:
#         value = json.loads(value)
#     flask.session[name] = value


# from .model.users import User
# def get_user(user_class=User):
#     username = getpass.getuser()
#     if username == "blgd":
#         username = "diedrich"

#     return user_class.select_one(
#         sql.where("login = ", sql.string_literal(username)))

# from . import authentication
# authentication.get_user = get_user
