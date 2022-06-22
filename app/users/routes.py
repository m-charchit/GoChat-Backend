from datetime import datetime, timedelta
from functools import wraps
import uuid
from flask import Blueprint,request,jsonify, make_response
import jwt
from  werkzeug.security import generate_password_hash, check_password_hash
from app import db,app
from app.middleware.check_login import login_required

from app.models import Detail  

users = Blueprint('users', __name__,url_prefix="/api/auth")


@users.route("/register",methods=["POST"])
def register():
    username,email = request.get_json().get("username"),request.get_json().get("email")
    password  = request.get_json().get("password")
    user = Detail.query.filter_by(username=username).first()
    if not user and username:
        # database ORM object
        user = Detail(
            public_id = str(uuid.uuid4()),
            username = username,
            email = email,
            password = generate_password_hash(password)
        )
        # insert user
        db.session.add(user)
        db.session.commit()
  
        return make_response('Successfully registered.', 201)
    else:
        # returns 202 if user already exists
        return make_response('User already exists. Please Log in.', 202)
    
    
@users.route("/login",methods=[ "POST"])
def signin():
    username,password = request.get_json().get("username"),request.get_json().get("password")
    
    if not username or not password:
        # returns 401 if any email or / and password is missing
        return make_response(
            'Could not verify',
            401,
            {'WWW-Authenticate' : 'Basic realm ="Login required !!"'}
        )
  
    user = Detail.query.filter_by(username = username).first()
  
    if not user:
        # returns 401 if user does not exist
        return make_response(
            'Could not verify',
            401,
            {'WWW-Authenticate' : 'Basic realm ="User does not exist !!"'}
        )
  
    if check_password_hash(user.password, password):
        # generates the JWT Token
        token = jwt.encode({
            'public_id': user.public_id,
            'exp' : datetime.utcnow() + timedelta(minutes = 30)
        }, app.config['SECRET_KEY'])
  
        return make_response(jsonify({'token' : token}), 201)
    # returns 403 if password is wrong
    return make_response(
        'Could not verify',
        403,
        {'WWW-Authenticate' : 'Basic realm ="Wrong Password !!"'}
    )
    
@users.route("/test",methods=["POST"])
@login_required
def test(current_user):
    print(current_user)
    return {"data":current_user.username}