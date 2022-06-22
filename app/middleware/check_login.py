from functools import wraps
from flask import request,jsonify
import jwt

from app import app
from app.models import Detail


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # jwt is passed in the request header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        # return 401 if token is not passed
        if not token:
            return jsonify({'message' : 'Token is missing !!'}), 401
  
        try:
            # decoding the payload to fetch the stored details
            print(app.config['SECRET_KEY'])
            data = jwt.decode(token, app.config['SECRET_KEY'],algorithms=['HS256'])
            current_user = Detail.query.filter_by(public_id = data['public_id']).first()
        except Exception as e:
            print(e)
            return jsonify({
                'message' : 'Token is invalid !!'
            }), 401
        # returns the current logged in users contex to the routes
        return  f(current_user, *args, **kwargs)
  
    return decorated