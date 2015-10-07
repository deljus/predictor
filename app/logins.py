__author__ = 'OV'
from app import login_manager
from app import pdb
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    user = pdb.get_user(user_id=user_id)
    if user:
        return User(**user)

    return None


class User(UserMixin):
    def __init__(self, **kwargs):
        self.__id = kwargs['id']
        self.__email = kwargs['email']
        self.__active = kwargs['active']

    def is_active(self):
        return self.__active

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def get_id(self):
        return self.__id

    def get_email(self):
        return self.__email




