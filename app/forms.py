__author__ = 'OV'
from app.models import db
from flask_wtf import Form
from wtforms import StringField, HiddenField, validators, \
    BooleanField, SubmitField, SelectField, PasswordField, ValidationError, SelectMultipleField, TextAreaField


class CheckExist(object):
    def __init__(self):
        self.message = 'User exist'

    def __call__(self, form, field):
        username = field.data
        if db.getuser(username):
            raise ValidationError(self.message)


class Registration(Form):
    email = StringField('email', [validators.DataRequired(), validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired(),
                                          validators.EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password', [validators.DataRequired()])
    submit_btn = SubmitField('Submit')

class Login(Form):
    email = StringField('email', [validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])
    submit_btn = SubmitField('Enter')

