#!/usr/bin/python
#-*- coding:utf-8 -*-


from flask import Flask, jsonify, render_template, send_from_directory
from kelidata import Device, Alarm, Alarmrecord, db
from keliComunicator import  KeliCommunicator
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/video/'

ALARMTYPE = {
    '4': '仪表绑定错误',
    '33': '电子铅封打开',
    '34': '仪表外壳打开',
    '35': '电子铅封打开',
    '36': '仪表绑定错误',
    '37': '电子铅封打开',
    '38': '仪表绑定错误',
    '39': '电子铅封打开',
    '40': '仪表外壳打开',
    '41': '电子铅封打开',
    '14': '仪表绑定错误',
    '54': '电子铅封打开',
    '55': '仪表绑定错误',
    '56': '电子铅封打开',
    '57': '仪表外壳打开',
    '58': '电子铅封打开',
    '59': '仪表绑定错误',
    '60': '电子铅封打开',
    '61': '电子铅封打开',
    '62': '仪表外壳打开',
    '63': '电子铅封打开',
    '64': '仪表绑定错误',
    '65': '电子铅封打开',
    '66': '仪表绑定错误',
    '67': '电子铅封打开',
    '68': '仪表外壳打开',
}


#渲染主页

@app.route('/', methods=['GET'])
def index():
    return render_template('Home.html')


@app.route('/api/', methods=['GET'])
def api():
    return render_template('api.html')


@app.route('/Home/', methods=['GET'])
def home():
    return render_template('Home.html')


@app.route('/Hotspot/', methods=['GET'])
def hotspot():
    return render_template('Hotspot.html')


@app.route('/Devices/', methods=['GET'])
def deviceList():
    return render_template('Devices.html')


# 全国设备分布情况
@app.route('/keli/api/v1.0/devices/', methods=['GET'])
def devices():
    devices_state = {}
    online_count = Device.query.filter(Device.inited == True).count()
    offline_count = Device.query.filter(Device.inited == False).count()
    devices_state["online"] = online_count
    devices_state["offline"] = offline_count
    devices_state["provinces"] = []

    province_status = {}
    for device in db.session.query(Device.province, db.func.count('*')).group_by(Device.province).filter(Device.inited==True, Device.province.isnot(None)).all():
        province_status[device[0]] = {'online': device[1]}
    for device in db.session.query(Device.province, db.func.count('*')).group_by(Device.province).filter(Device.inited==False,Device.province.isnot(None)).all():
        if device[0] in province_status:
            province_status[device[0]]['offline'] = device[1]
        else:
            province_status[device[0]] = {'offline': device[1], 'online': 0}
    for k, v in province_status.items():
        devices_state['provinces'].append({'province': k, 'online': v['online'], 'offline': v['offline'] if 'offline' in v else '0'})
    return jsonify(devices_state)


# 根据省份查询设备在线非在线数量
@app.route('/keli/api/v1.0/devices/province/count/<string:province>', methods=['GET'])
def province(province):
    devices_count = {}

    online_count = Device.query.filter(Device.inited == True, Device.province.like('%%%s%%'%province), Device.province.isnot(None)).count()
    offline_count = Device.query.filter(Device.inited == False, Device.province.like('%%%s%%'%province), Device.province.isnot(None)).count()
    devices_count['online'] = online_count
    devices_count['offline'] = offline_count
    return jsonify(devices_count)


# 根据省份过滤，返回设备信息列表
@app.route('/keli/api/v1.0/devices/province/<string:province>/<int:page>', methods=['GET'])
def provinceDetails(province,page):

    devicesDetails = Device.query.join(Alarm, Device.gprsSn == Alarm.gprsSn).group_by(Device.company).\
        filter(Device.province.like('%%%s%%'%province), Device.province.isnot(None)).order_by(db.desc(Device.company)).add_entity(Alarm).paginate(page, per_page=8, error_out=False)
    detailsCount = Device.query.join(Alarm, Device.gprsSn == Alarm.gprsSn).group_by(Device.company). \
        filter(Device.province.like('%%%s%%'%province), Device.province.isnot(None)).count()
    devices_count = {}
    devices_count['detailsCount'] = detailsCount
    devices_count['devicesDetails'] = []
    for item in devicesDetails.items:
        device = item[0]
        alarm = ALARMTYPE[item[1]] if item[1] in ALARMTYPE else item[1]
        device = device.json_details()
        device['almNum'] = alarm.almNum
        devices_count['devicesDetails'].append(device)
    return jsonify(devices_count)


# 设备之所属公司列表
@app.route('/keli/api/v1.0/devices/province/<string:province>/companys', methods=['GET'])
def companys(province):
    companys=Device.query.group_by(Device.company, Device.company.isnot(None)).filter(Device.province.like('%%%s%%'%province)).order_by(db.desc(Device.company))
    devices_company = []
    for company in companys:
        if company.company != "":
            devices_company.append({'name': company.company})
    return jsonify({'company': devices_company})


# 根据省份和公司名称查询设备在线非在线数量
@app.route('/keli/api/v1.0/devices/province/<string:province>/company/count/<string:company>', methods=['GET'])
def company_count(province,company):
    devices_count = {}
    online_count = Device.query.filter(Device.inited == True, Device.province.like('%%%s%%'%province), Device.company == company).count()
    offline_count = Device.query.filter(Device.inited == False, Device.province.like('%%%s%%'%province), Device.company == company).count()
    devices_count['online'] = online_count
    devices_count['offline'] = offline_count
    return jsonify(devices_count)


# 根据省份和公司名称过滤，返回设备信息列表
@app.route('/keli/api/v1.0/devices/province/<string:province>/company/<string:company>/<int:page>', methods=['GET'])
def companyDetails( province,company,page):
    companyCount = Device.query.join(Alarm, Device.gprsSn == Alarm.gprsSn).filter(Device.province.like('%%%s%%'%province), \
                                                            Device.company == company).add_entity(Alarm).count()
    companyDetails = Device.query.join(Alarm, Device.gprsSn == Alarm.gprsSn).filter(Device.province.like('%%%s%%'%province),\
                            Device.company == company).order_by(db.desc(Device.company)).add_entity(Alarm).paginate(page, per_page=8, error_out=False)
    deviceCompanyDetails = {}
    deviceCompanyDetails['detailsCount'] = companyCount
    deviceCompanyDetails['devicesDetails'] = []
    for item in companyDetails.items:
        device = item[0]
        alarm = ALARMTYPE[item[1]] if item[1] in ALARMTYPE else item[1]
        device = device.json_details()
        device['almNum'] = alarm.almNum
        deviceCompanyDetails['devicesDetails'].append(device)
    return jsonify(deviceCompanyDetails)


# 指定设备的故障详细信息,例如设备编号001
@app.route('/keli/api/v1.0/device/<string:gprsSn>/alarms/<int:page>', methods=['GET'])
def alarms(gprsSn, page):
    communicator = KeliCommunicator()
    communicator.getDevicesAlarms(gprsSn)
    devicesCountry = Alarmrecord.query.filter(Alarmrecord.gprsSn == '001').paginate(page, per_page=6, error_out=True)
    devicesCount = Alarmrecord.query.filter(Alarmrecord.gprsSn == '001').count()
    devicePup={}
    devicePup['devicesCount'] = devicesCount
    devicePup['devicesCountry'] = []
    for item in devicesCountry.items:
        device = item.json_alarm()
        devicePup['devicesCountry'].append(device)
    return jsonify(devicePup)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')
