from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@127.0.0.1:3306/keli'
db = SQLAlchemy(app)

class Device(db.Model):
    __tablename__ = 'device'
    gprsSn = db.Column(db.String(20), primary_key=True)
    company = db.Column(db.String(32), unique=True)
    addr = db.Column(db.String(32))
    inited = db.Column(db.String(10))
    stat = db.Column(db.String(10))
    almCode = db.Column(db.String(10))
    almAddr = db.Column(db.String(10))
    t = db.Column(db.String(50))
    ip = db.Column(db.String(50))
    location = db.Column(db.String(50))
    serviceInfo = db.Column(db.String(300))
    province = db.Column(db.String(50))
    city = db.Column(db.String(50))

    def __repr__(self):
        return "<Device %r>" % self.gprsSn

#设备详细信息
    def json_details(self):
        return {
            'gprsSn': self.gprsSn,
            'company': self.company if self.company != ""and self.company != None  else"宁波柯力创安科技股份有限公司",
            'inited': "在线" if self.inited=='1' else"离线",
            'stat': "故障" if self.stat != '0' else "正常",
            'almCode': self.almCode,
            'serviceInfo': self.serviceInfo if self.serviceInfo != "" else "无"
        }

class Alarm(db.Model):
    __tablename__='alarm'
    gprsSn = db.Column(db.String(20), primary_key=True)
    almNum = db.Column(db.String(50), unique=True)

    def __repr__(self):
        return "<Alarm %r>" % self.gprsSn


class Alarmrecord(db.Model):
    __tablename__ = 'alarmrecord'
    id = db.Column(db.Integer, primary_key=True)
    gprsSn = db.Column(db.String(20))
    recordTime = db.Column(db.DateTime(0))
    code = db.Column(db.String(10))
    addr = db.Column(db.String(10))
    deviceType = db.Column(db.String(20))
    stat = db.Column(db.String(10))

    def __repr__(self):

        return "<AlarmRecord %r>" % self.gprsSn


    # 故障信息
    def json_alarm(self):
        return {
            'recordTime': self.recordTime,
            'code': self.code,
            'addr': self.addr,
            'stat': self.stat
        }



