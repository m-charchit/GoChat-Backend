from app import db
from datetime import datetime
from app import login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return Detail.query.get(int(user_id))



class Detail(db.Model,UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(35),unique=True, nullable=False)
    email = db.Column(db.String(35),  nullable=False)
    password = db.Column(db.String(300), nullable=False)
    status = db.Column(db.String(21),default="secondary")
    pic = db.Column(db.String(51),default="default.jpg")
    last_active = db.Column(db.DateTime,default=datetime.now())
    otp_timing = db.Column(db.DateTime)
    otp =  db.Column(db.String(7),nullable=True)
    email_confirmed =  db.Column(db.Boolean, nullable=False, default=False)
    notification_id = db.Column(db.String(68))
    user_message1 = db.relationship("Message", backref="owner",cascade="all, delete, delete-orphan")
    blocked_users =  db.relationship("Blocks",backref="blocker")
    # def __init__()

class Blocks(db.Model):
    sno = db.Column(db.Integer,primary_key=True)
    user = db.Column(db.String(35),db.ForeignKey("detail.username"))
    user2 = db.Column(db.String(35))


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    msg = db.Column(db.String(2000))
    msg_type =  db.Column(db.String(6))
    username = db.Column(db.String(35),db.ForeignKey("detail.username"))
    get_user = db.Column(db.String(35))
    time = db.Column(db.DateTime)


# from app import db,create_app
# from app.models import *
# app = create_app()
# with app.app_context():
#     db.create_all()