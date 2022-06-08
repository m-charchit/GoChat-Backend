from app import mail
from PIL import Image
from flask_login import current_user
import os
import secrets
from flask import  flash
from app.firebase import storage,firebase_user,firebase

def send_mail(otp=None,email=None):
   	mail.send_message("OTP for login into Chatapp",
                sender="charchit.dahiya@gmail.com",
                recipients=[email],
                body =  "Please use this otp for login in to your account\n" + str(otp)
                )

def save_picture(form_picture):
    random_hex = str(secrets.token_hex(15))
    ext = os.path.splitext(form_picture.filename)[1]
    file_path = random_hex + current_user.username +str(ext) 

    output_size = (100,100) 
    i = Image.open(form_picture)
    i.thumbnail = output_size
    i.save(file_path) # Save picture at picture path
    storage.child(file_path).put(file_path) # Upload to firebase
    os.remove(file_path)
    
    try:
        storage.delete(current_user.pic,firebase_user["idToken"])
        flash('Old picture removed', 'success')
    except:
        pass

    return  file_path