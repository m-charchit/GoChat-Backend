from  flask import Flask,Blueprint,render_template,session,request,redirect,flash,url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_user, current_user, logout_user, login_required
from app import socketio,db,bcrypt
from flask_socketio import emit, send
from app.users.forms import RegistrationForm,LoginForm,Account,ChangeEmail,Confirm_email,ResetPassword
from app.models import *
from app.users.utils import send_mail,save_picture
from random import randint
from datetime import datetime
from app.firebase import storage,firebase_user

users = Blueprint('users', __name__)

@users.route("/register",methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash("It looks like You are already Registered","info")
        return redirect("/")
    form = RegistrationForm()
    if request.method=="POST" and form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = Detail(username=form.username.data,email=form.email.data,password=hashed_password)
        db.session.add(user)
        db.session.commit()
        socketio.emit('regis' ,user.username,broadcast=True)
        return redirect("/")
    return render_template("register.html",form=form,register=True)

@users.route("/confirm_email",methods=["POST","GET"])
@login_required
def confirm_email():
    if current_user.email_confirmed :
        return redirect("/")
    form = Confirm_email()
    if request.method == "POST" and form.validate_on_submit():
            current_user.email_confirmed = True
            db.session.commit()
            flash("E-mail confirmed successfully","success")
            return redirect("/edit_profile")
    return render_template("register.html",register=False,form=form)



@users.route("/signin",methods=["GET", "POST"])
def signin():
    if current_user.is_authenticated:
        flash("It looks like you are already logined to site","info")
        return redirect("/")
    form = LoginForm()
    if request.method=="POST" and form.validate_on_submit():
        user = Detail.query.filter_by(username=form.username.data).first()
        print(user)
        if user != None and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Logined successfully","success")
        else:
            flash("Unsuccessful Login. Please Try Again","danger")
            return redirect(request.args.get("next") if request.args.get("next") else "/signin") 

        return redirect(request.args.get("next") if request.args.get("next") else "/") 

    return render_template("signin.html",form=form)

@users.route("/logout",methods=["POST"])
def logout():
    logout_user()
    flash("You successfully logged out","success")
    return redirect("/signin")

@users.route("/edit_profile",methods=["GET", "POST"])
@login_required
def edit():
    socketio.emit("editing_profile",current_user.username,broadcast=True)
    current_user.status = "edit"
    db.session.commit()
    if current_user.email_confirmed == False:
        flash("Please Confirm Your E-mail address to Continue","info")
        return redirect("/confirm_email")

    form  = Account()
    if request.method == "POST" :
        if form.validate_on_submit():
            if current_user.username != form.username.data:
                print("hi")
                socketio.emit('username_changed' ,{"old":current_user.username,"new":form.username.data},broadcast=True)
            current_user.username = form.username.data
            if form.pic.data:
                picture_file = save_picture(form.pic.data)
                current_user.pic = picture_file

            current_user.password = bcrypt.generate_password_hash(form.New_password.data).decode('utf-8') if form.New_password.data != "" else current_user.password
            current_user.time = datetime(1000, 1, 1, 1, 1, 1) 
            current_user.otp = ""
            db.session.commit()
            flash("Profile Upadated Successfully","success")
            return redirect("/edit_profile")

    form.username.data = current_user.username
    image_file = current_user.pic
    url = storage.child(image_file).get_url(firebase_user['idToken']) if image_file !="default.jpg" else url_for('static',filename='images/default.jpg')

    return render_template("account.html",form=form,pic_url=url)

@users.route("/reset_email",methods=["POST","GET"])
@login_required
def email():
    import os
    print(os.environ.get("CONFIG"))
    form = ChangeEmail()
    if request.method == "POST" and form.validate_on_submit():
        current_user.email = form.email.data
        current_user.time = datetime(1000, 1, 1, 1, 1, 1) 
        current_user.otp = ""
        db.session.commit()
        flash("Email Changed Successfully","success")
        return redirect("/reset_email")
    return render_template("reset_email.html",form=form)

@users.route("/reset_password",methods=["POST","GET"])
def password():
    if current_user.is_authenticated:
        return redirect("/")
    form = ResetPassword()
    if request.method == "POST" and form.validate_on_submit():
        user =  Detail.query.filter_by(username=form.username.data).first()
        if user:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user.password = hashed_password
            user.time = datetime(1000, 1, 1, 1, 1, 1) 
            user.otp = ""
            db.session.commit()
            flash("Password Changed Successfully","success")
        return redirect("/signin")
    return render_template("reset_password.html",form=form)    


@users.route("/otp",methods=["POST"])
def otp():
    if request.method == "POST":
        email = request.form.get("email")
        cur_user = current_user
        if not current_user.is_authenticated :
            User = Detail.query.filter_by(username=request.form.get("username")).first()
            if User:
                cur_user = User
            else:
                return {"user":False,"error":"No User exists with that username"}
        cur_user.otp =  str(randint(121211,999299))
        cur_user.otp_timing = datetime.utcnow()
        db.session.commit()
        if email :
            send_mail(cur_user.otp,email)
        else:
            send_mail(cur_user.otp,cur_user.email)
        return "otp sent!"

@users.route("/delete_account",methods=["POST"])
@login_required
def delete_account():
    if request.method == "POST":
        if str(request.form.get("otp")) != str(current_user.otp) or  (datetime.utcnow() - current_user.otp_timing).seconds / 60 > 1:
            print(request.form.get("otp"))
            if (datetime.utcnow() - current_user.otp_timing).seconds / 60 > 5:
                print("sfs")
                current_user.otp = ""
                current_user.otp_timing = datetime(1000, 1, 1, 1, 1, 1)
                db.session.commit()
                print(current_user.otp_timing)
            return "Invalid OTP"
        else:
            User = Detail.query.filter_by(username=current_user.username).first()
            msgs = Message.query.filter_by(username=current_user.username).delete()
            User.password = bcrypt.generate_password_hash("mx234jw39g2").decode('utf-8')
            User.email = ""
            User.status = "deleted" 
            User.email_confirmed = False
            if User.pic != "default.jpg":
                storage.delete(current_user.pic,firebase_user["idToken"])
            User.pic = "default.jpg"
            User.otp = ""
            db.session.commit()
            flash("Account deleted successfully!","success")
            socketio.emit('account_delete' ,current_user.username,broadcast=True)
            logout_user()
            return "deleted"


