import urllib.request
import json

def ipConvert(ip):
    ak = "Sdgaxxi1EVnSvx15pQQTlpDMVGyjcB4C"
    url = "http://api.map.baidu.com/location/ip?ak=%s&ip=%s"%(ak, ip)
    with urllib.request.urlopen(url) as f:
        content = json.loads(f.read().decode('utf-8'))
        return content

