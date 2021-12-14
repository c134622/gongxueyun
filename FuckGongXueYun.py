import json
import threading
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from binascii import a2b_hex
import base64
import time
import requests
import ssl
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import hashlib


class FuckGongXueYun:
    _Admin = "管理者邮箱"

    def __init__(self, phone, password, email, country, province, city, address,
                 longitude, latitude):
        self.phone = phone
        self.password = password
        self.email = email
        self.country = country
        self.province = province
        self.city = city
        self.address = address
        self.longitude = longitude
        self.latitude = latitude
        self.planId = None
        self.token = None
        self.planId_sign = None
        self.sign_in_sign = None
        self.userId = None
        self.moguNo = None

    @staticmethod
    def md5(word):
        hl = hashlib.md5()
        hl.update(word.encode(encoding="utf-8"))
        return hl.hexdigest()

    @staticmethod
    def bytesToHexString(bs):
        return ''.join(['%02X ' % b for b in bs])

    @staticmethod
    def encrypt(word, key="23DbtQHR2UMbH6mJ"):
        key = key.encode('utf-8')
        mode = AES.MODE_ECB
        aes = AES.new(key, mode)
        pad_pkcs7 = pad(word.encode('utf-8'), AES.block_size, style='pkcs7')  # 选择pkcs7补全
        encrypt_aes = aes.encrypt(pad_pkcs7)
        encrypted_text = FuckGongXueYun.bytesToHexString(encrypt_aes)
        return encrypted_text.replace(" ", "").lower()

    def login(self):
        t = str(int(time.time()) * 1000)
        login_data = {
            "phone": self.phone,
            "password": self.password,
            "uuid": "",
            "loginType": "android",
            "t": t,
        }
        url = "https://api.moguding.net:9000/session/user/v1/login"
        headers = {
            'Content-Type': 'application/json; charset=UTF-8'
        }
        try:
            response_login = requests.post(url, data=json.dumps(login_data), headers=headers)
            json_data = response_login.json()
            self.token = json_data.get("data")["token"]
            self.userId = json_data.get("data")["userId"]
            self.planId_sign = FuckGongXueYun.md5(self.userId + "student" + "3478cbbc33f84bd00d75d7dfa69e0daa")
            self.moguNo = json_data.get("data")["moguNo"]
            return True
        except Exception as e:
            print(e, e.__traceback__.tb_lineno)
            if self.email != self._Admin:
                self.send_email(self.email, "登录失败，已联系管理员")
            self.send_email(self._Admin,
                            f"错误函数: LOGIN\n{self.phone}--{e}\nERROR_Line{e.__traceback__.tb_lineno}")
            return None

    def get_planId(self):
        url = "https://api.moguding.net:9000/practice/plan/v3/getPlanByStu"
        try:
            response = requests.post(
                url=url,
                data=json.dumps({"paramsType": "student"}),
                headers={
                    'authorization': self.token,
                    'Content-Type': 'application/json; charset=UTF-8',
                    'roleKey': 'student',
                    "sign": self.planId_sign
                }
            )
            self.planId = response.json()['data'][0]["planId"]
            self.sign_in_sign = FuckGongXueYun.md5(
                "Android" + "START" + self.planId + self.userId + self.address + "3478cbbc33f84bd00d75d7dfa69e0daa")
            print(self.phone + ": " + self.planId)

            return True
        except Exception as e:
            print("打卡失败")
            print(e, e.__traceback__.tb_lineno)
            if self.email != self._Admin:
                self.send_email(self.email, "获取参数失败，已联系管理员")
            self.send_email(self._Admin,
                            f"错误函数: PlanID\n{self.phone}--{e}\nERROR_Line{e.__traceback__.tb_lineno}")
            return None

    def sign_in(self):
        if self.sign_in_sign is None:
            if self.email != self._Admin:
                self.send_email(self.email, "所需参数为空，无法进行签到请求，已联系管理员")
            self.send_email(self._Admin, "所需参数为空，无法进行签到请求--" + self.phone + "\n" + str(self.planId))
            return None
        t = str(int(time.time()) * 1000)
        info = {
            "phone": self.phone,
            "country": self.country,
            "province": self.province,
            "city": self.city,
            "address": self.address,
            "longitude": self.longitude,
            "latitude": self.latitude,
        }
        data_dict = {
            "device": "Android",
            "planId": self.planId,
            "country": self.country,
            "province": self.province,
            "city": self.city,
            "address": self.address,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "t": FuckGongXueYun.encrypt(t),
            "description": "",
            "type": "START",
            "attendanceType": ""
        }
        url = 'https://api.moguding.net:9000/attendence/clock/v2/save'
        headers = {
            'Host': 'api.moguding.net:9000',
            "user-agent": "Mozilla/5.0 (Linux; U; Android 10; zh-cn; AQM-AL10 Build/HONORAQM-AL10) AppleWebKit/533.1 (KHTML, like Gecko) Version/5.0 Mobile Safari/533.1",
            'authorization': self.token,
            'Content-Type': 'application/json; charset=UTF-8',
            'roleKey': 'student',
            "sign": self.sign_in_sign,
        }
        with open("./log/Sign.log", "a", encoding="utf-8") as f:
            try:
                sign_response = requests.post(url=url, data=json.dumps(data_dict), headers=headers)
                json_data = sign_response.json()
                if json_data['code'] == 200:
                    f.write(f"{self.phone}--{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}--签到成功\n")
                    self.send_email(self.email,
                                    '签到成功' + '\n' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()) + json.dumps(
                                        info, ensure_ascii=False))
                else:
                    if self.email != self._Admin:
                        self.send_email(self._Admin, '签到失败' + '\n' + json.dumps(json_data, ensure_ascii=False))
                    f.write(f"{self.phone}--{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}--签到失败\n")
                    self.send_email(self.email, '签到失败' + '\n' + json.dumps(json_data, ensure_ascii=False))
            except Exception as e:
                if self.email != self._Admin:
                    self.send_email(self.email, "签到失败，已联系管理员")
                self.send_email(self._Admin,
                                f"错误函数: SIGN_IN\n{self.phone}--{e}\nERROR_Line{e.__traceback__.tb_lineno}")

    def send_email(self, receivers, data):
        sender = '发送者邮箱'
        auth_passport = ''  # auth_passport QQ邮箱首页设置——账户——POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务——生成授权码
        server = smtplib.SMTP()
        server.connect('smtp.qq.com')
        server.login('登陆者邮箱', auth_passport)
        subject = f'打卡信息 --{self.phone}'
        message = MIMEText(data, 'plain', 'utf-8')
        message['From'] = Header('打卡消息', 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')
        try:
            server.sendmail(sender, receivers, message.as_string())
            return None
        except Exception as e:
            print(e)
            print("邮件发送失败")
            return -1

    def main(self):
        log_res = self.login()
        if log_res is not None:
            planId_res = self.get_planId()
            if planId_res is not None:
                self.sign_in()


def task(phone_, password_, email_, country_, province_, city_, address_, longitude_, latitude_):
    sign = FuckGongXueYun(phone_, password_, email_, country_, province_, city_, address_,
                          longitude_, latitude_)
    sign.main()


def main():
    with open("./info.json", "r", encoding="utf-8") as f:
        info = json.loads(f.read()).get("info")
        for i in info:
            phone = i.get("phone")
            password = i.get("password")
            email = i.get("email")
            country = i.get("country")
            province = i.get("province")
            city = i.get("city")
            address = i.get("address")
            longitude = i.get("longitude")
            latitude = i.get("latitude")
            Sign_Task = threading.Thread(target=task, args=(phone, password, email, country, province, city, address,
                                                            longitude, latitude))
            Sign_Task.start()

if __name__ == '__main__':
    main()

