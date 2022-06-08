import functools
import os
import secrets

from app import db, pushy, socketio
from app.firebase import firebase_user, storage
from app.main.utils import *
from app.models import *
from flask import (Blueprint, Flask, Response, abort,
                   render_template, request, session, url_for)
from flask_login import current_user, login_required
from flask_socketio import disconnect, emit
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, delete, or_, select

users = {}
sids = {}

def authenticated_only(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            disconnect()
        else:
            return f(*args, **kwargs)
    return wrapped

# jsonpickle.encode(user), mimetype='application/json' use this to send list

main = Blueprint('main', __name__)


@socketio.on('connect')
def test_connect(auth):
    if not current_user.is_anonymous:
        sids[request.sid] = current_user.username
        emit('status', {'user': current_user.username,"status":"Online"},broadcast=True)
        current_user.status = "Online"
        db.session.commit()

@socketio.on('connected')
def get_id(data):
    if not current_user.is_anonymous:
        sids[request.sid] =  current_user.username + "user_contact"

@socketio.on('disconnect')
def test_disconnect():
    if not current_user.is_anonymous:
        cur_sid = sids[request.sid]
        del sids[request.sid]
        if not cur_sid.endswith("user_contact") and not cur_sid in [i for  i in sids.values()]:
            current_user.last_active =  datetime.utcnow()
            db.session.commit()

        if not cur_sid in [i for i in sids.values()] or (not cur_sid in [i for i in sids.values()] and cur_sid.endswith("user_contact")) :

            emit('status', {'user': current_user.username,"status":format_date()},broadcast=True)
            # if cur_sid in [i for  i in users.values()]:

            current_user.status = format_date()
            db.session.commit()
        print('Client disconnected')


@socketio.on('get_data')
@authenticated_only
def get_data(data):
    if not current_user.is_anonymous and not userDeleted(data["user"]):
        msgs =  Message.query.filter(Message.id > data["last_id"],Message.username==current_user.username,Message.get_user==data["user"]).all()
        a = {}
        for i in msgs:
                a[i.id] = {"msg":i.msg,"msg_type":i.msg_type,"time":str(i.time),"user":i.username}
                
        emit("rec_data",{"message":a,"status":Detail.query.filter_by(username=data["user"]).first().status})
        
    

def sendFile(data):
    request.namespace = ""
    request.sid = ""
    print(data)
    if not current_user.is_anonymous and not userDeleted(data["user"]):
        block = Blocks.query.filter_by(user2=current_user.username).all()
        print(block)
        for i in list(sids):
            if (sids[i] == data["user"] or sids[i] == current_user.username or ((sids[i][:len(sids[i]) - 12] == data["user"] or sids[i][:len(sids[i]) - 12] == current_user.username) and sids[i].endswith("user_contact"))) and sids[i] not in [i.user for  i in block]:
                print(sids[i],print(i),"thisi is")
                emit("file",data,room=i)


@socketio.on('typing')
@authenticated_only
def typing(data):
    if not current_user.is_anonymous and not userDeleted(data["user"]):
        for i in list(sids):
            if sids[i] == data["user"] or sids[i] == current_user.username or ((sids[i][:len(sids[i]) - 12] == data["user"] or sids[i][:len(sids[i]) - 12] == current_user.username) and sids[i].endswith("user_contact")):
                emit("type",{"typing":data["typing"],"user":current_user.username},room=i)
                    

@socketio.on('idle')
@authenticated_only
def idle(data):
    print(data)
    if not current_user.is_anonymous and current_user.status[0:4] != "Last":
        emit("user_idle",{"stat":data["status"],"username":current_user.username},broadcast=True)

        current_user.status = "Idle" if data["status"] == "Idle" else "Online"

        db.session.commit()
        print(current_user.status)

@socketio.on('block')
@authenticated_only
def block_user(data):
    if not  current_user.is_anonymous:
        for i in list(sids):
            if   sids[i] == current_user.username or (sids[i].endswith("user_contact") and  sids[i][:len(sids[i]) - 12] == current_user.username):
                emit("block",{"type":data["type"],"user":data["user"]},room=i)
        if data["type"] == "unblock":
            block = Blocks.query.filter_by(user=current_user.username,user2=data["user"]).first()
            db.session.delete(block)
        else:
            block = Blocks(user=current_user.username,user2=data["user"])
            db.session.add(block)

        db.session.commit()


@socketio.on('change')
@authenticated_only
def handle_change(data):
    if not current_user.is_anonymous:
        if current_user.username == data["current_user"]:
            block = Blocks.query.filter_by(user2=current_user.username).all()
            print(data)
            for i in list(sids):
                if sids[i] == data["user"] or sids[i] == current_user.username or ((sids[i][:len(sids[i]) - 12] == data["user"] or sids[i][:len(sids[i]) - 12] == current_user.username) and sids[i].endswith("user_contact")) and sids[i] not in [i.user for  i in block] :
                    emit("change_ok",{"user":current_user.username,"id":data["id"],"type":data["type"]},room=i) 

            if data["type"] == "user_d":
                msg = Message.query.filter_by(id=data["id"],msg_type="left",username=current_user.username,get_user=data["user"]).first()
                try:
                    if not Message.query.filter_by(id=int(data["id"])-1).first():
                        storage.delete(msg.msg.split("?")[0].split("/")[-1],firebase_user["idToken"])
                except Exception as e:
                    print(e)
                db.session.delete(msg)
            elif data["type"] == "cur_d_me":
                msg = Message.query.filter_by(id=data["id"],msg_type="right",username=current_user.username,get_user=data["user"]).first()

                print(msg)
                try:
                    if not Message.query.filter_by(id=int(data["id"])+1).first():
                        storage.delete(msg.msg.split("?")[0].split("/")[-1],firebase_user["idToken"])
                except Exception as e:
                    print(e)
                db.session.delete(msg)
            if data["type"] == "cur_d_all":
                try:
                    file_msg = Message.query.filter_by(id=data["id"],username=current_user.username).first()
                    if file_msg.msg.startswith("https://firebasestorage.googleapis"):
                        storage.delete(file_msg.msg.split("?")[0].split("/")[-1],firebase_user["idToken"])

                except Exception as e:
                    print(e)
                msg1 = db.session.query(Message).filter(
                    and_(or_(Message.id==data["id"],Message.id==int(data["id"])+1),or_(Message.username == current_user.username,and_(Message.username == data["user"],Message.get_user == current_user.username,Message.msg_type == "left")))).delete()

        db.session.commit()
        return "removed"

@socketio.on('delete_all_msg')
@authenticated_only
def handle_message(data):
    if not current_user.is_anonymous:
        if current_user.username == data["current_user"]:
            emit("deleted_all")
            file_msg = Message.query.filter_by(username=current_user.username,get_user=data["user"]).all()
            for i in file_msg:
                if i.msg.startswith("https://firebasestorage.googleapis"):
                    ID = i.id + 1 if i.msg_type == "right" else i.id -1 
                    if not Message.query.filter_by(id=ID).first():
                        storage.delete(i.msg.split("?")[0].split("/")[-1],firebase_user["idToken"])

            msgs = Message.query.filter_by(username=current_user.username,get_user=data["user"]).delete()
            db.session.commit()

@socketio.on('message')
@authenticated_only
def handle_message(data):
    if not current_user.is_anonymous  and not userDeleted(data["user"]):
        print(data)
        if data["user"] in [i.user2 for i in current_user.blocked_users]:
            return "You need to unblock to send messages to user!"
        if len(data["msg"]) < 2000:
            block = Blocks.query.filter_by(user2=current_user.username).all()
            rec_user = Detail.query.filter_by(username=data["user"]).first()
            print(rec_user.status)
            msg = Message(msg=data["msg"],msg_type="right",get_user=data["user"],owner=current_user,time=datetime.utcnow())
            db.session.add(msg)
            if data["user"] not in [i.user for  i in block]:
                msg1 = Message(msg=data["msg"],msg_type="left",get_user=current_user.username,owner=rec_user,time=datetime.utcnow())        
                db.session.add(msg1)
            db.session.flush()

            for i in list(sids):
                if (sids[i] == data["user"] or sids[i] == current_user.username or ((sids[i][:len(sids[i]) - 12] == data["user"] or sids[i][:len(sids[i]) - 12] == current_user.username) and sids[i].endswith("user_contact"))) and sids[i] not in [i.user for  i in block]:
                    print(sids[i],sids[i] not in [i.user for  i in block])
                    print(data,current_user.username)
                    user_stat = rec_user.status
                    emit('msg', {"msg":data["msg"],"user":current_user.username,"rec_user":rec_user.username,"status":rec_user.status,"date":format_date(),"id":msg.id} , room=i)
            if rec_user.status != "Online" and rec_user.status != "Idle" and data["user"] not in [i.user for  i in block]:
                    notification = {'message':f"{current_user.username} - {data['msg']}",'url':'https://charchit-chat.herokuapp.com/chat/' + current_user.username,'image':'https://img.icons8.com/ios/50/000000/weixing.png',"title":"New Message from ChatApp"}
                    try:
                        pushy.push(rec_user.notification_id,notification)
                        print("sent")
                    except Exception as e:
                        print(e)
            db.session.commit()
            return "Message sent!"
        else:
            emit("error_msg",{"error":"Limit of sending 2000 characters message exceeded"})

@main.app_template_filter('get_img')
def get_img(img):
    return storage.child(img).get_url(firebase_user["idToken"]) if img != "default.jpg" else url_for('static',filename='images/default.jpg')




@main.route("/")  
@login_required
def index():
    users = Detail.query.filter(Detail.username!=current_user.username,).all()
    # message = current_user.user_message1
    a,b= [],[]
    for i in users:
        message = Message.query.filter_by(username=current_user.username,get_user=i.username).order_by(Message.id.desc()).first()

        msg = Message.query.filter(Message.username==current_user.username,Message.get_user==i.username,Message.time > current_user.last_active).all()
        d = Message.query.filter(Message.username==current_user.username,Message.get_user==i.username).all()
        b.append(msg)    
        a.append(message)
    return render_template("users.html",users=users,msg=a,unseen_msg=b,blocked_users=[i.user2 for i in current_user.blocked_users])


@main.route("/chat/<user>",methods=['POST','GET'])
@login_required
def chat(user):
    User = Detail.query.filter(Detail.username==user,Detail.username!=current_user.username).first()
    if request.method == "POST":
        not_id = request.form.get('id')
        if not_id:
            current_user.notification_id = not_id
            db.session.commit()

        elif request.files.get('file'):
            file = request.files['file']
            random_hex = str(secrets.token_hex(15))
            ext = os.path.splitext(file.filename)[1]
            file_path = random_hex + current_user.username + "chat" +str(ext) 

            file.save(file_path) # Save picture at picture path
            storage.child(file_path).put(file_path) # Upload to firebase
            os.remove(file_path)
            fileUrl = storage.child(file_path).get_url(firebase_user["idToken"])

            block = Blocks.query.filter_by(user2=current_user.username).all()
            rec_user = Detail.query.filter_by(username=user).first()
            msg = Message(msg=fileUrl,msg_type="right",get_user=user,owner=current_user,time=datetime.utcnow())
            db.session.add(msg)
            if user not in [i.user for  i in block]:
                msg1 = Message(msg=fileUrl,msg_type="left",get_user=current_user.username,owner=rec_user,time=datetime.utcnow())        
                db.session.add(msg1)
            db.session.flush()
            data = {"msg":fileUrl,"user":user,"current_user":current_user.username,"date":format_date(),"id":msg.id}
            socketio.on_event('file_uploaded', sendFile(data))
            db.session.commit()

        elif request.form.get('no'):
            no = int(request.form.get('no'))
            msgs = Message.query.filter_by(username=current_user.username,get_user=User.username).order_by(Message.time).all()
            print(len(msgs))
            if 0 <len(msgs) - no < 30 :
                msgs = msgs[:len(msgs) -no]
            else:
                msgs = msgs[len(msgs)- (no + 30) :len(msgs) - no]
            print(msgs)
            a = {}
            for i in msgs:
                a[i.id] = {"msg":i.msg,"msg_type":i.msg_type,"time":i.time,"user":i.username}
            return a
        return "ok"

    if not User:
        abort(404)
    block = Blocks.query.filter_by(user=current_user.username,user2=user).first()
    message = Message.query.filter_by(username=current_user.username,get_user=User.username).order_by(Message.time).all()
    message = message[len(message) - 10:]
    return render_template("index.html",user=User,message=message,block=block) 

@main.route("/service-worker.js",methods=['POST','GET'])
def return_file():
    return Response("importScripts('https://sdk.pushy.me/web/1.0.8/pushy-service-worker.js');", mimetype='  text/javascript')


    
    
    


