from flask_wtf import FlaskForm 
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField,IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_login import current_user
from app.models import *
from app import bcrypt
from datetime import datetime


def validate_username(form, username):
    user = Detail.query.filter_by(username=username.data).first()
    if user :
        raise ValidationError('Username already exists.')


def validate_password(form,password):
    print(password.data)
    if not bcrypt.check_password_hash(current_user.password, password.data):
        raise ValidationError('password incorrect')

def validate_otp(form,otp):
    if str(otp.data) != str(current_user.otp) or  (datetime.utcnow() - current_user.otp_timing).seconds / 60 > 5:
        if (datetime.utcnow() - current_user.otp_timing).seconds / 60 > 1:
            current_user.otp = ""
            current_user.otp_timing = datetime(1000, 1, 1, 1, 1, 1)

            db.session.commit()
            print(current_user.otp_timing)
        raise ValidationError('Invalid OTP')

def validate_email(form, email):
    user = Detail.query.filter_by(email=email.data).first()
    if user:
        raise ValidationError('Email already exists.')

class RegistrationForm(FlaskForm):
    username = StringField('Username',
                        validators=[DataRequired(), Length(min=5, max=20), validate_username])
    email = StringField('Email',
                        validators=[DataRequired(), Email(), validate_email, Length(min=0,max=35)])
    password = PasswordField('Password',
                        validators=[DataRequired(), Length(min=8, max=60)])
    confirm_password = PasswordField('Confirm Password',
                        validators=[DataRequired(), Length(min=8, max=60), EqualTo('password')])
    submit = SubmitField('Submit')

            


class LoginForm(FlaskForm):
    # Validate required fields from user for sign in
    username = StringField('Username',
                        validators=[DataRequired(), Length(min=5, max=20)])
    password = PasswordField('Password',
                        validators=[DataRequired(), Length(min=8, max=60)])
    # recaptcha = RecaptchaField('Please complete the verification below to sign in') # Used to prevent bots brute force sign ins
    remember = BooleanField("Remember Me")
    submit = SubmitField('Submit')

class Account(FlaskForm):
    username =  StringField('Change Username',validators=[DataRequired(), Length(min=5, max=20) ])

    pic = FileField('Update profile picture', validators=[FileAllowed(['jpg','png','jpeg'])])

    password = PasswordField('Old Password',
                        validators=[DataRequired(), Length(min=8, max=60), validate_password])
    New_password = PasswordField('New Password')
    confirm_password = PasswordField('Confirm Password',
                        validators=[EqualTo('New_password')])
    otp = IntegerField('Enter OTP',validators=[DataRequired(),validate_otp])
    submit = SubmitField('Update Details')

    def validate_new_password(self,New_password):
        if New_password != "":
            if len(New_password) < 8 or len(New_password) > 60:
                raise ValidationError('Field must be between 8 and 60 characters long.')

    def validate_new_username(form, username):
        user = Detail.query.filter_by(username=username.data).first()
        if user and username.data != current_user.username:
            raise ValidationError('Username already exists.')


class ChangeEmail(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email(),validate_email])
    confirm_email = StringField('Confirm Email',
                        validators=[DataRequired(), Email(), EqualTo('email')])
    password = PasswordField('Password',
                        validators=[DataRequired(), Length(min=8, max=60), validate_password])

    email_otp = IntegerField('Enter OTP',validators=[DataRequired(), validate_otp])

    submit = SubmitField('Update Email')

class Confirm_email(FlaskForm):
    otp = IntegerField('Enter OTP',validators=[DataRequired(),validate_otp])

    submit = SubmitField('Confirm email')


class ResetPassword(FlaskForm):
    username =  StringField('Change Username',validators=[DataRequired(), Length(min=5, max=20) ])
    otp = IntegerField('Enter OTP',validators=[DataRequired()])
    password = PasswordField('New Password',
                        validators=[DataRequired(), Length(min=8, max=60)])
    confirm_password = PasswordField('Confirm Password',
                        validators=[DataRequired(), Length(min=8, max=60), EqualTo('password')])
    submit = SubmitField('Change Password')

    def check_user(self,username):
        user = Detail.query.filter_by(username=username.data).first()
        if user == None:
            raise ValidationError('No User exists with that username!')


    def check_otp(self,otp,username):
        User =  Detail.query.filter_by(username=username.data).first()
        if str(otp.data) != str(User.otp) or  (datetime.utcnow() - User.otp_timing).seconds / 60 > 5:
            if (datetime.utcnow() - User.otp_timing).seconds / 60 > 1:
                User.otp = ""
                User.otp_timing = datetime(1000, 1, 1, 1, 1, 1)

                db.session.commit()
                print(User.otp_timing)
        raise ValidationError('Invalid OTP')
