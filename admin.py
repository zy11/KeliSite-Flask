# -*- coding:utf-8-*-
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
from kelidata import Device, Alarm, Alarmrecord, db

app = Flask(__name__)

if __name__ == '__main__':
    admin = Admin(app, name='keli后台', template_mode='bootstrap3')
    path = os.path.join(os.path.dirname(__file__), 'static')
    admin.add_view(ModelView(Device, db.session))
    admin.add_view(ModelView(Alarm, db.session))
    admin.add_view(ModelView(Alarmrecord, db.session))
    admin.add_view(FileAdmin(path, '/static/', name='Static Files'))
    app.run(debug=False, host='0.0.0.0', port=5001)