from datetime import datetime
from app.models import Detail

def format_date(date=None): 
	return  datetime.utcnow().strftime("%Y %b %d %H:%M:%S") 

def userDeleted(user):
	return True if Detail.query.filter_by(username=user,status="deleted").first() else False