#!/usr/bin/python
#-*- coding: utf-8 -*-
import datetime
import json
import logging
import os
import pickle
import time
from os import path

from lxml import etree

import requests
from bs4 import BeautifulSoup

YOUR_BADGE = " "
YOUR_PASSWORD = " "
YOUR_DOMAIN = " "

Log_PATH='/home/bodytemp_autofill.log'
IS_DEBUG=False

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

sessions = requests.session()

mainurl=" "
getdataurl=" "
recorddataurl=" "

def check_for_auth(response, *args, **kwargs):
    if response.status_code == 200 and 'General Access Authentication' in response.text:
        getvalue(databody,response.text)
        databody.update({'domain_username':YOUR_DOMAIN+'\\'+YOUR_BADGE})
        databody.update({'domain_password':YOUR_PASSWORD})
        response =sessions.post(response.url,headers = headers,data=databody)
        if response.status_code== 401:
            log.error('account and password not match')
            exit()
        elif response.status_code == 200 :
            if 'General Access Authentication' in response.text:
                log.error('error occur while post account and password ,check for post password structure')
                exit()
            else:
                with open('./bodytemp_cookie.tmp', 'wb') as f:
                    pickle.dump(sessions.cookies, f)
        elif response.status_code == 500:
            log.error('server error')
            exit()

def getvalue(data,html):
    selector = etree.HTML(html)
    value = selector.xpath('//input[@class="form-control" or @type="hidden" or @id="login_button"]')
    # //form//*[self::input[@type!="submit"] or self::input[@id="login_button"]]
    # 剔除submit的button，多个button会冲突的
    for result in value:
        if "value" not in result.attrib:
            data.update({result.attrib['id']:''})
            log.debug("update hidden input ：" + result.attrib['id'] + "=" )
        else:
            data.update({result.attrib['id'] : result.attrib['value']})
            # value为空没关系，属性没有必定会抛异常，这种没value的只会出现在不需要input的地方
            log.debug("update hidden input ：" + result.attrib['id'] + "=" + result.attrib['value'])
#json解析为类
class JSONObject:
    def __init__(self, d):
        self.__dict__ = d

databody={
}

getdata ={
    'badge': YOUR_BADGE
    }

headers = {
    "content-type": "application/x-www-form-urlencoded",
    'user-agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.45 Safari/537.36 Edg/79.0.309.30"
    }

recorddata = {
    'badge' :YOUR_BADGE,
    'status' :'3',
    'temperature' :'36.3'
}

runingtime = datetime.datetime.now()
submorning = runingtime - datetime.datetime.now().replace(hour=8,minute=59,second=55,microsecond=0)
subafternoon = runingtime -datetime.datetime.now().replace(hour=13,minute=59,second=55,microsecond=0)

if runingtime.strftime("%p") == 'AM' and 0<= submorning.total_seconds() <= 3600  :
    log.debug("when application running at"+runingtime.strftime('%Y-%M-%d')+"9 clock in hours")
    recorddata.update({'temperature':'36.3'})
elif runingtime.strftime("%p") == 'PM' and 0<= subafternoon.total_seconds() <=3600:
    log.debug("when application running at"+runingtime.strftime(' %d %b %Y')+"14 clock in hours")
    recorddata.update({'temperature':'36.7'})
    # 变一下，下午的就记36.7度
else:
    log.debug("neither 9 or 14 clock , application exit")
    # 不是9点也不是14点就退出进程
    exit()

# 本地有就先读取cookie信息
if path.exists("./bodytemp_cookie.tmp"):
    with open('./bodytemp_cookie.tmp', 'rb') as f:
        sessions.cookies.update(pickle.load(f))

response = sessions.get(getdataurl,  headers=headers,  hooks={'response': check_for_auth})

headers.update({"content-type": "application/json"})
response = sessions.post(getdataurl,headers =headers,json=getdata)

cValue = json.loads(response.text, object_hook=JSONObject)
for p in cValue.d:
    print(p.__type, p.ReportDate, p.Temperature, sep='\t', end='\n')

sub = datetime.datetime.now()-datetime.datetime.strptime(cValue.d[0].ReportDate, '%m/%d/%Y %H:%M:%S')
# 判断最后一个记录超过两个小时，就记录
if sub.total_seconds() > 3600*2 :
    log.debug('is been two hour before application running time, add a record')
    headers.update({"content-type": "application/json"})
    response = sessions.post(recorddataurl,headers =headers,json=recorddata)
    response = sessions.post(getdataurl,headers =headers,json=getdata)
    cValue = json.loads(response.text, object_hook=JSONObject)
    for p in cValue.d:
        print(p.__type, p.ReportDate, p.Temperature, sep='\t', end='\n')
else:
    log.debug('theres a record in two hour ,will not record')