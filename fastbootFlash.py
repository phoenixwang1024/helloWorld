# -*- coding: utf-8 -*-
"""
Created on Thu Oct 10 13:31:51 2019
@author: phoenix.wang
"""

import os,serial,datetime,time,requests,re,subprocess
import xml.etree.ElementTree as ET

#  获取xml文件路劲和要生成的bat文件名称
def getPath( ):
    global batName
    global filePath
    global dirPath
    global execBatFlag

    while True:
        dirPath = input('输入路径，或者把包含partition_nand.xml的update文件夹拖到此处：>>> ')
        filePath = dirPath + '/partition_nand.xml'
        if os.path.isdir(dirPath):
            if not os.path.exists(filePath):
                print('未找到partition.xml文件，请确保路径是否正确并重试！\n')
            else:
                break
        else:
            print('请确保输入路径为文件夹，而不是文件！')

    batNameInput = input('输bat名称,不带.bat后缀:>>> ')
    if batNameInput == '':
        batName = 'cmd.bat'
    else:
        batName = batNameInput + '.bat'
    #  获取输入以确定是否生成bat文件同时执行分区执行的指令
    while True:
        execBatFlagIn = input('请选择生成bat文件同时是否自动开始升级，1==升级，2==不升级:>>> ')
        if execBatFlagIn == '1' or execBatFlagIn == '2':
            execBatFlag = int(execBatFlagIn)
            break
        else:
            print('输入错误，请选择1或者2:')

def makeBat(filePath,batName):
    fbat = open('./'+batName,'w+')
    fxml = open(filePath,'r')

    fbat.write('set path=' + dirPath + '\r\n')
    tree = ET.parse('partition_nand.xml')
    root = tree.getroot()

    for child in root:
        for partition in child:
            if partition.tag == 'partition':
                for item in partition:
                    if item.tag == 'name':
                        a1 = item.text[2:].lower()
                    if item.tag == 'img_name':
                        a2 = item.text
                        if a2 is not 'appshoot.mbn':
                            fbat.seek(0, 2)
                            strToWrite = 'fastboot flash ' + a1+ ' %path%/' + a2 + '\r\n'
                            fbat.write(strToWrite)
                            fcommand = 'fastboot flash ' + a1 + ' ' + dirPath + '/' + a2
                            if execBatFlag == 1:
                               os.system(fcommand)
    if execBatFlag == 1:
        os.system('fastboot reboot')
    fbat.write('\r\nfastboot reboot\r\npause')
    fbat.close()
    fxml.close()
    print(' \033[1;35m bat文件生成成功，文件路径: \033[0m!', os.path.abspath(batName))

def ser(SPN, baudRate=115200,):  # 连接端口
    global serPort

    try:
        serPort = serial.Serial(SPN, baudRate, bytesize=8, parity='N', stopbits=1, timeout=1)
        checkPort = serPort.isOpen()
        if checkPort:
            serPort.close()
    except serial.serialutil.SerialException as e:
            serPort.close()
    serPort = serial.Serial(SPN, baudRate, bytesize=8, parity='N', timeout=1, xonxoff=False, rtscts=False,
                            write_timeout=None, dsrdtr=False, inter_byte_timeout=None)
#  串口执行AT指令，funcFlag默认0，不打印返回数据，如果配置为1，会返回上报信息
def excuteCommand(command,funcFlag=0):
    global adbKey
    atCommand = command.encode('utf-8')
    serPort.write(atCommand)

    if funcFlag == 1:
        #print(time.strftime("[%Y-%m-%d %H:%M:%S]", time.localtime()) + command.replace('\r\n',''))
        serOut = serPort.read(size=1024)
        string_AT_R = serOut.decode(encoding="UTF-8", errors="strict")
        string_AT_R_array = string_AT_R.split('\r\n')
        for i in string_AT_R_array:
            print(time.strftime("[%Y-%m-%d %H:%M:%S]:", time.localtime()) + i + "\n")
            adbKeyRegex = re.compile(r'QADBKEY: ([\d]*)')
            adbKeyResult = re.findall(adbKeyRegex, i)
            if adbKeyResult:
                adbKey = adbKeyResult[0]
                return adbKey


#  查询debug密码，默认adb，可配置：qtyp='console'
def query_key(adbKey, qversion='v1.0', qtype='adb'):
    if adbKey:
        url1 = 'http://192.168.10.11:8080/job/query_key/build?delay=0sec'
        reResult = 1

        global header
        cookie = r'htmlAudioNotificationsEnabled=false; jenkins-timestamper-offset=-28800000; screenResolution=1920x1080; JSESSIONID.50763f5b=node0eed4ricnv1bc14enhx3mdkt4l937.node0'
        header={
            'Connection': 'keep-alive',
            'Cookie': cookie,
            'Host': '192.168.10.11:8080',
            'Origin': 'http://192.168.10.11:8080',
            'Referer': 'http://192.168.10.11:8080/job/query_key/build?delay=0sec',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36',
        }

        formData = {}
        json = '{"parameter": [{"name": "qversion", "value": "'+ qversion + '"}, {"name": "ID", "value": "' + adbKey + '"}, {"name": "qtype", "value": "'+ qtype + '"}], "statusCode": "303", "redirectTo": "."}'
        formData['json'] = json
        formData['Submit'] = 'Build'
        #response1 = requests.post(url1, headers=header, data=formData)    #  发送adb key查询密码

        buildHistoryUrl = 'http://192.168.10.11:8080/job/query_key/buildHistory/all'
        response3 = requests.get(buildHistoryUrl, headers=header)
        idRegex = re.compile('<a update-parent-class=".build-row" href="/job/query_key/([\d]*)/" class="tip model-link inside build-link display-name">')
        #print('History request: ', response3.text)
        currentID = re.findall(idRegex, response3.text)[0]
        print('current: ', currentID)

        while reResult:
            url2 = 'http://192.168.10.11:8080/job/query_key/' + currentID + '/console'
            response2 = requests.get(url2, headers = header)
            #print(response2.status_code)
            #print(response2.text)
            adbRegex1 = re.compile('\+\+ sh genkey.sh v1.0 ([\d]+)')
            match_adb_key = re.findall(adbRegex1, response2.text)
            #print(match_adb_key)
            if match_adb_key[0] == adbKey:
                adbRegex2 = re.compile(r'您所查询的密钥为：(.*)')
                result = re.findall(adbRegex2, response2.text)
                debug_key = result[1]
                print('Key: ', debug_key)
                reResult = 0
                return debug_key
            else:
                currentID =str(int(currentID)-1)
    else:
        debug_key = 'quectel123'
        return debug_key


# 初始化函数
def preparation():
    excuteCommand("ATE1V1\r\n", 0)
    excuteCommand("AT+CMEE=1\r\n", 0)
    excuteCommand('AT+QURCCFG="URCPORT","uart1"\r\n', 0)
    excuteCommand("AT&W\r\n", 0)


if __name__ == "__main__":

    SPN = 'com3'
    baudRate = 115200
    serialType = 'uart1'
    #ser(SPN,baudRate)
    #countFlag = input('How many times need to run? ')
    #i=1

    #preparation()
    # excuteCommand("ATI\r\n", 1)  # 查看版本信息
    # excuteCommand("AT+CSUB\r\n", 1)
    # excuteCommand("AT+EGMR=0,5\r\n", 1)
    # excuteCommand("AT+EGMR=0,7\r\n", 1)

    #adbKey = excuteCommand("AT+QADBKEY?\r\n", 0)
    #adbPW = query_key(adbKey)
    #adbIN = 'AT+QADBKEY="' + adbPW + '"\r\n'
    #excuteCommand(adbIN,0)
    #excuteCommand('AT+QCFG="usbcfg",0x2C7C,0x0121,1,1,1,1,1,1,1\r\n', 0)
    #excuteCommand("AT+QFASTBOOT\r\n", 0)
    getPath()
    makeBat(filePath, batName)
    time.sleep(25)

    # ser(SPN, baudRate)
    # preparation()
    # #a = os.system('cmd.exe ./batName')
    # excuteCommand("ATI\r\n", 1)
    # excuteCommand("AT+CSUB\r\n", 1)
    # excuteCommand("AT+EGMR=0,5\r\n", 1)
    # excuteCommand("AT+EGMR=0,7\r\n", 1)
    # excuteCommand('AT+QCFG="usbcfg",0x2C7C,0x0121,1,1,1,1,1,0,0\r\n', 1)


