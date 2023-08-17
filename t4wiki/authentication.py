import functools

from flask import g, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import Unauthorized, Forbidden

class User(object):
    """
    Abstract base class for any user.
    """
    def __init__(self, login):
        self.login = login

    @staticmethod
    def anonymous_user():
        """
        Return an object of your user class that represents a
        user not logged in.
        """
        return AnonymousUser()

    @classmethod
    def by_login(cls, login):
        raise NotImplementedError()

    @property
    def roles(self):
        """
        Return a set of roles this user has.
        t4wiki knows about three roles: UserManager and Writer.
        A user may be authenticated but have no roles.
        """
        raise NotImplementedError()

    def has_role(self, *roles):
        """
        Return True if this user has one of the roles passed as
        arguements.
        """
        for role in roles:
            if role in self.roles:
                return True

        return False

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return (not self.is_anonymous)

    @property
    def is_manager(self):
        return self.has_role("Manager")

    @property
    def is_writer(self):
        return self.has_role("Writer")

class AnonymousUser(User):
    roles = set()
    is_root = False
    is_anonymous = True
    is_authenticated = False

    is_manager = False
    is_writer = False

    login = None

    def has_role(self, *roles):
        return False


_user_class = User
def set_user_class(user_class):
    global _user_class
    _user_class = user_class


def get_user() -> User:
    user_login = session.get("user_login")

    if user_login is None:
        return _user_class.anonymous_user()
    else:
        if "user" not in g:
            g.user = _user_class.by_login(user_login)

        return g.user

def login_required(func):
    @functools.wraps(func)
    def wrapped_func(*args, **kwargs):
        if get_user().is_anonymous:
            raise Unauthorized()
        return func(*args, **kwargs)

    return wrapped_func

class role_required:
    def __init__(self, *roles):
        self.roles = roles

    def __call__(self, func):

        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            if not get_user().has_role(*self.roles):
                raise Forbidden()

            return func(*args, **kwargs)

        return wrapped_func
