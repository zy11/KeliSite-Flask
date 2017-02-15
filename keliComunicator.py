#!/usr/bin/python
#-*- coding:utf-8 -*-
import os
import socket
from ctypes import *
import struct
import time
import configparser
import threading
import datetime
import ipConversion
import logging
from logging.handlers import TimedRotatingFileHandler
from kelidata import db, Device, Alarmrecord, Alarm


class KeliProtocolPdu(Structure):
    _fields_ = [
        ("head",            c_ubyte, 4),
        ("code",            c_ushort),
        ("state",           c_ushort),
        ("flag",            c_ushort),
        ("padding",         c_uint),
        ("crc",             c_ushort),
    ]

    def __init__(self, head=0x89abcdef, code=b"duanjunying"):
        self.head = 0x89abcdef
        self.code = 0x0080
        self.state = 0
        self.flag = 1
        # self.crc = crc16.crc16xmodem(b'123456789')

class KeliCommunicator:
    def __init__(self):
        self.maxBuffLength = 5000000
        self.deviceCode = 0x0080
        self.alrmCode = 0x0081
        self.alrmDetailCode = 0x0082
        self.headerLength = 50
        self.devPduLength = 352
        self.alarmStructLength = 12
        self.alarmStructDetailLength = 20

        self.keliServers = []
        self.socketBuffLength = 8902
        # self.codes = [0x0080, 0x0081, 0x0082]
        self.codes = [0x0080, 0x0081]
        self.lastsn = ""
        conf = configparser.ConfigParser()
        conf.read("servers.ini")
        for site in conf.sections():
            serverIp = conf.get(site, 'ip')
            serverPort = int(conf.get(site, 'port'))
            sockobj = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sockobj.connect((serverIp, serverPort))
            sockobj.settimeout(2)
            self.keliServers.append({'ip': serverIp, 'port': serverPort, 'socket': sockobj})

        LOGGING_DATE_FORMAT	= '%Y-%m-%d %H:%M:%S'
        logging.basicConfig(level=logging.DEBUG, datefmt=LOGGING_DATE_FORMAT)
        self.logger = logging.getLogger('keliCommunicator')
        fh = TimedRotatingFileHandler(filename=os.path.join('keliComunicator.log'), when="midnight", interval=1, backupCount=2)
        fh.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        self.logger.debug('Keli pull Start!')

    def keli_crc(self,buff,bufflen,code):
        CRC_HI = [
            0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,  0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
            0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,  0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
            0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,  0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
            0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,  0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
            0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,  0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,
            0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,  0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
            0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40,  0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,
            0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40, 0x01, 0xC0, 0x80, 0x41,  0x01, 0xC0, 0x80, 0x41, 0x00, 0xC1, 0x81, 0x40
        ]

        CRC_LO = [0x00, 0xC0, 0xC1, 0x01, 0xC3, 0x03, 0x02, 0xC2, 0xC6, 0x06, 0x07, 0xC7, 0x05, 0xC5, 0xC4, 0x04, 0xCC, 0x0C, 0x0D, 0xCD, 0x0F, 0xCF, 0xCE, 0x0E,  0x0A, 0xCA, 0xCB, 0x0B, 0xC9, 0x09, 0x08, 0xC8,
            0xD8, 0x18, 0x19, 0xD9, 0x1B, 0xDB, 0xDA, 0x1A, 0x1E, 0xDE, 0xDF, 0x1F, 0xDD, 0x1D, 0x1C, 0xDC, 0x14, 0xD4, 0xD5, 0x15, 0xD7, 0x17, 0x16, 0xD6,  0xD2, 0x12, 0x13, 0xD3, 0x11, 0xD1, 0xD0, 0x10,
            0xF0, 0x30, 0x31, 0xF1, 0x33, 0xF3, 0xF2, 0x32, 0x36, 0xF6, 0xF7, 0x37, 0xF5, 0x35, 0x34, 0xF4, 0x3C, 0xFC, 0xFD, 0x3D, 0xFF, 0x3F, 0x3E, 0xFE,  0xFA, 0x3A, 0x3B, 0xFB, 0x39, 0xF9, 0xF8, 0x38,
            0x28, 0xE8, 0xE9, 0x29, 0xEB, 0x2B, 0x2A, 0xEA, 0xEE, 0x2E, 0x2F, 0xEF, 0x2D, 0xED, 0xEC, 0x2C, 0xE4, 0x24, 0x25, 0xE5, 0x27, 0xE7, 0xE6, 0x26,  0x22, 0xE2, 0xE3, 0x23, 0xE1, 0x21, 0x20, 0xE0,
            0xA0, 0x60, 0x61, 0xA1, 0x63, 0xA3, 0xA2, 0x62, 0x66, 0xA6, 0xA7, 0x67, 0xA5, 0x65, 0x64, 0xA4, 0x6C, 0xAC, 0xAD, 0x6D, 0xAF, 0x6F, 0x6E, 0xAE,  0xAA, 0x6A, 0x6B, 0xAB, 0x69, 0xA9, 0xA8, 0x68,
            0x78, 0xB8, 0xB9, 0x79, 0xBB, 0x7B, 0x7A, 0xBA, 0xBE, 0x7E, 0x7F, 0xBF, 0x7D, 0xBD, 0xBC, 0x7C, 0xB4, 0x74, 0x75, 0xB5, 0x77, 0xB7, 0xB6, 0x76,  0x72, 0xB2, 0xB3, 0x73, 0xB1, 0x71, 0x70, 0xB0,
            0x50, 0x90, 0x91, 0x51, 0x93, 0x53, 0x52, 0x92, 0x96, 0x56, 0x57, 0x97, 0x55, 0x95, 0x94, 0x54, 0x9C, 0x5C, 0x5D, 0x9D, 0x5F, 0x9F, 0x9E, 0x5E,  0x5A, 0x9A, 0x9B, 0x5B, 0x99, 0x59, 0x58, 0x98,
            0x88, 0x48, 0x49, 0x89, 0x4B, 0x8B, 0x8A, 0x4A, 0x4E, 0x8E, 0x8F, 0x4F, 0x8D, 0x4D, 0x4C, 0x8C, 0x44, 0x84, 0x85, 0x45, 0x87, 0x47, 0x46, 0x86,  0x82, 0x42, 0x43, 0x83, 0x41, 0x81, 0x80, 0x40
        ]

        if buff==None or bufflen <= 0:
            return 0xa5a5
        precrc = 0xff
        nextcrc = 0xff
        for i in range(bufflen):
            index = precrc^buff[i]
            precrc = nextcrc^CRC_HI[index]
            nextcrc = CRC_LO[index]
        # print(precrc + (nextcrc<<8))
        return precrc + (nextcrc<<8)+ 12764

    def createProtocol(self, code, pduLength, state=0, flag=1):
        protocalHead = 0x89abcdef
        user_name = bytes('duanjunying', encoding="utf8")
        password = bytes('123456', encoding="utf8")
        prebuffer = create_string_buffer(pduLength)
        struct.pack_into("I", prebuffer, 0, protocalHead)
        struct.pack_into("I", prebuffer, 4, 32)
        struct.pack_into("H", prebuffer, 8, code)
        struct.pack_into("H", prebuffer, 10, state)
        struct.pack_into("H", prebuffer, 12, flag)
        # struct.pack_into("H", prebuffer, 16, crc16.crc16xmodem(prebuffer[0:16]))
        struct.pack_into("H", prebuffer, 16, self.keli_crc(prebuffer[0:16], 16, code))
        struct.pack_into("16s", prebuffer, 18, user_name)
        struct.pack_into("16s", prebuffer, 34, password)
        struct.pack_into("H", prebuffer, 50, self.keli_crc(prebuffer[0:50], 50, code))
        return prebuffer

    def createAlarmRecordProtocol(self, code, sn, pduLength, state=0, flag=1):
        protocalHead = 0x89abcdef
        user_name = bytes('duanjunying', encoding="utf8")
        password = bytes('123456', encoding="utf8")
        prebuffer = create_string_buffer(pduLength)
        struct.pack_into("I", prebuffer, 0, protocalHead)
        struct.pack_into("I", prebuffer, 4, 40)
        struct.pack_into("H", prebuffer, 8, code)
        struct.pack_into("H", prebuffer, 10, state)
        struct.pack_into("H", prebuffer, 12, flag)
        struct.pack_into("H", prebuffer, 16, self.keli_crc(prebuffer[0:16], 16, code))
        struct.pack_into("16s", prebuffer, 18, user_name)
        struct.pack_into("16s", prebuffer, 34, password)
        struct.pack_into("!Q", prebuffer, 50, sn)
        crc = self.keli_crc(prebuffer[0:58], 58, code)
        if crc > 0xffff:
            crc = crc&0xffff
        struct.pack_into("H", prebuffer, 58, crc)
        return prebuffer

    def getData(self, code):
        if(code != 0x0082):
            cmd = self.createProtocol(code, 52)
        for service in self.keliServers:
            sock = service['socket']
            data = sock.send(cmd.raw)
            self.recvProcessBySocket(sock)

    def recvProcessBySocket(self, sock):
        buff = b''
        while True:
            try:
                buff += sock.recv(self.socketBuffLength)
                time.sleep(1)
            except socket.timeout as timeout:
                break
        try:
            self.pduProcess(buff)
        except Exception as e:
            self.logger.error(e)


    def allSocketRecvProcess(self):
        for server in self.keliServers:
            buff = b''
            sockobj = server['socket']
            while True:
                try:
                    buff +=sockobj.recv(self.socketBuffLength)
                    time.sleep(1)
                except socket.timeout as timeout:
                    sockobj.close()
                    break
            self.pduProcess(buff)

    def pduHeaderParser(self, buff):
        return struct.unpack_from("IIH", buff, 0)[2]

    def getCode(self, buff):
        return struct.unpack_from("IIH", buff, 0)[2]

    def devicesPduProcess(self, buff):
        for index in range(int(len(buff)/self.devPduLength)):
            try:
                unpacked = struct.unpack_from("!Q32s32sBBBB8sIQ256s", buff[index * self.devPduLength:(index + 1) * self.devPduLength], 0)
                gprsSn = hex(unpacked[0])

                try:
                    company = unpacked[1].decode(encoding='gb2312').replace(b'\x00'.decode(encoding='gbk'), "")
                except Exception as e:
                    try:
                         company =unpacked[1].dacode(encoding='gbk').replace(b'\x00'.decode(encoding='gbk'), "")
                    except Exception as e:
                         company = None
                try:
                    addr = unpacked[2].decode(encoding='gb2312').replace(b'\x00'.decode(encoding='gbk'), "")
                except Exception as e:
                    try:
                        addr = unpacked[2].decode(encoding='gbk').replace(b'\x00'.decode(encoding='gbk'), "")
                    except Exception as e:
                        addr = None
                        # self.logger.error(e)
                        # self.logger.error(unpacked)
                inited = unpacked[3]
                stat = unpacked[4]
                almCode = unpacked[5]
                almAddr = unpacked[6]
                try:
                    t = datetime.datetime(*struct.unpack_from("HBBBBB", unpacked[7], 0))
                except Exception as e:
                    t = None
                try:
                    ip = socket.inet_ntoa(struct.pack('I', socket.htonl(unpacked[8])))
                except Exception as e:
                    ip = '122.227.181.134'

                location = unpacked[9]
                try:
                    serviceInfo = unpacked[10].decode(encoding='gb2312').replace(b'\x00'.decode(encoding='gbk'), "")
                except Exception as e:
                    try:
                        serviceInfo = unpacked[10].decode(encoding='gbk').replace(b'\x00'.decode(encoding='gbk'), "")
                    except Exception as e:
                        serviceInfo = None

                query = Device.query.filter(Device.gprsSn == gprsSn)
                if query.first():
                    query.update({
                        Device.inited: inited,
                        Device.stat: stat,
                        Device.almCode: almCode,
                        Device.almAddr: almAddr,
                        Device.t: t,
                        Device.serviceInfo: serviceInfo
                    })
                else:
                    try:
                        temp = ipConversion.ipConvert(ip)
                        city = temp['content']['address_detail']['city']
                        try:
                            province = temp['content']['address_detail']['province']
                        except Exception as e:
                            province = None
                    except Exception as e:
                        city = None
                        city = None
                        province = None

                    device = Device(gprsSn=gprsSn, company=company, addr=addr, inited=inited, stat=stat,
                                    almCode=almCode,
                                    almAddr=almAddr, t=t, ip=ip, location=location, serviceInfo=serviceInfo, province=province,
                                    city=city,)
                    db.session.add(device)
            except Exception as e:
                self.logger.error(e)
                self.logger.error(unpacked)
        db.session.commit()

    def alarmsPduProcess(self,buff):
        for index in range(int(len(buff)/self.alarmStructLength)):
            unpacked = struct.unpack_from("!QI", buff[index*self.alarmStructLength:(index+1)*self.alarmStructLength],0)
            gprsSn = hex(unpacked[0])
            almNum = unpacked[1]
            query = Alarm.query.filter(Alarm.gprsSn == gprsSn)
            if query.first():
                query.update({
                    Alarm.almNum: almNum
                })
            else:
                alarm = Alarm(gprsSn=gprsSn, almNum=almNum)
                db.session.add(alarm)
        db.session.commit()

    def alarmRecordsPduProcess(self, buff):
        for index in range(int(len(buff)/self.alarmStructDetailLength)):
            unpacked = struct.unpack_from("!QQBBBB",buff[index*self.alarmStructDetailLength:(index+1)*self.alarmStructDetailLength],0)
            gprsSn = hex(unpacked[0])
            try:
                recordTime = datetime.datetime(*struct.unpack_from("HBBBBBB", unpacked[1], 0))
            except Exception as e:
                recordTime = None
            code = unpacked[2]
            addr = unpacked[3]
            deviceType = unpacked[4]
            stat = unpacked[5]
            query = Alarmrecord.query.filter(Alarmrecord.gprsSn == gprsSn)
            if query.first():
                query.update({
                    Alarmrecord.recordTime: recordTime,
                    Alarmrecord.code: code,
                    Alarmrecord.addr: addr,
                    Alarmrecord.deviceType: deviceType,
                    Alarmrecord.stat: stat
                })
            else:
                alarmrecord = Alarmrecord(gprsSn=gprsSn, recordTime=recordTime, code=code, addr=addr, stat=stat)
                db.session.add(alarmrecord)
        db.session.commit()

    def pduProcess(self, buff):
        # self.logger.debug(buff)
        if buff == b'':
            return
        code = self.getCode(buff[0:self.headerLength])
        payLoad = buff[self.headerLength:-2]
        if code == self.deviceCode:
            # self.logger.debug(payLoad)
            unCompressBuff, buffLength = self.lzwDecode(payLoad, len(payLoad))
            self.devicesPduProcess(unCompressBuff)
        elif code == self.alrmCode:
            self.alarmsPduProcess(payLoad)
        elif code == self.alrmDetailCode:
            self.alarmRecordsPduProcess(payLoad)
        else:
            print('pass error')

    def getDevicesAlarmDataFromServer(self, sock):
        # 遍历devices数据库
        deviceGprsSn = Device.query.group_by(Device.gprsSn).all()
        for device in deviceGprsSn:
            cmd = self.createAlarmRecordProtocol(0x8002, eval(device.gprsSn), 60)
            sock.send(cmd.raw)
            self.recvProcessBySocket(sock)

    def getDataByServer(self, sock):
        for code in self.codes:
            if code != 0x8002:
                cmd = self.createProtocol(code, 52)
            data = sock.send(cmd.raw)
            self.recvProcessBySocket(sock)
        self.getDevicesAlarmDataFromServer(sock)


    def lzwDecode(self,data, datalen):
        lzw = cdll.LoadLibrary('LZW.dll')
        decodeLength = create_string_buffer(4)
        buff = create_string_buffer(self.maxBuffLength)
        lzw.LzwDecode(data, datalen, buff, decodeLength)
        rawLength = int(struct.unpack_from("I", decodeLength, 0)[0])
        return buff[0:rawLength], rawLength

    def pull(self):
        for server in self.keliServers:
            t = threading.Thread(target=self.getDataByServer,args=(server['socket'],))
            t.start()

    def main(self):
        while True:
            # todo current time > midnighttime //
            communicator = KeliCommunicator()
            communicator.pull()
            time.sleep(36000)

    def getDevicesAlarms(self,sn):
        for server in self.keliServers:
            sock = server['socket']
            cmd = self.createAlarmRecordProtocol(0x8002, eval(sn) if isinstance(sn,str) else sn, 60)
            sock.send(cmd.raw)
            self.recvProcessBySocket(sock)

if __name__ == '__main__':
    communicator = KeliCommunicator()
    communicator.main()

