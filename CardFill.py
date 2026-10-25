import os
import random

from PIL import Image, ImageDraw
import requests
import json
import urllib3
from io import BytesIO

# 测试环境证书过期, 跳过SSL校验
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

print(11111111)
def fillImage(lc):
    draw.rectangle((lc['x'], lc['y'], lc['x'] + lc['w'], lc['y'] + lc['h']), fill='black', outline='black')


def singleFill(gp):
    for j in gp['areas']:
        area = j['area']
        index = random.randint(0, len(area) - 1)
        fillImage(area[index])
        break


def markDir(filePath):
    if not os.path.exists(filePath):
        os.makedirs(filePath)


# 图片访问加密, 通过签名接口换取带OSS签名的临时访问地址
def signUrlMap(urlList):
    urlMap = {}
    for _i in range(len(urlList)):
        urlMap[str(_i + 1)] = urlList[_i]
    data = requests.post(domain + ossSignUrl, headers=headers, json={'urlMap': urlMap}, verify=False).text
    try:
        result = json.loads(data)
        return result['data']
    except Exception:
        raise Exception(data)


def saveTempImag(imageList):
    if imageList is not None and len(imageList) > 0:
        markDir(tempDir)
        # 清理上次运行残留的临时图片, 避免listdir混入脏文件
        for _f in os.listdir(tempDir):
            os.remove(os.path.join(tempDir, _f))
        rawUrls = [image['imgUrl'] for image in imageList]
        signedUrls = signUrlMap(rawUrls)
        for _i in range(1, len(imageList) + 1):
            key = str(_i)
            if key not in signedUrls:
                raise Exception('签名接口未返回图片地址: ' + rawUrls[_i - 1])
            url = signedUrls[key]
            print('template image' + str(_i), url)
            r = requests.get(url, verify=False)
            if r.status_code != 200:
                raise Exception('模板图片下载失败, status=' + str(r.status_code) + ', url=' + url)
            # 校验下载内容确实是图片, 否则报出响应内容便于排查(如OSS AccessDenied)
            try:
                Image.open(BytesIO(r.content)).verify()
            except Exception:
                raise Exception('模板图片内容无效, url=' + url + ', 响应内容: ' + r.content[:200].decode('utf-8', errors='replace'))
            save = tempDir + 'temp' + str(_i).zfill(3) + '.jpg'
            with open(save, 'wb') as output:
                output.write(r.content)
            _i = _i + 1
    else:
        raise Exception('缺少模板图片')


def findTemp():
    data = requests.get(domain + cardInfoUrl + cardId, headers=headers, verify=False).text
    try:
        result = json.loads(data)
        # print('result', result)
        for _h in result['groups']:
            groups.append(_h)
        saveTempImag(result['pages'])
    except Exception:
        raise Exception(data)


# def findCardId():
#     data = requests.get(domain + cardIdUrl + paperId, headers=headers, verify=False).text
#     try:
#         result = json.loads(data)
#         print('xxxxxx',data)
#         return result['data']['cardId']
#     except Exception:
#         # print('Exception',data)
#         raise Exception(data)
def findCardId():
    data = requests.get(domain + getPaperCard, headers=headers, verify=False).text
    # print(domain + getPaperCard)
    try:
        result = json.loads(data)
        # print('xxxxxx',data)
        return result['data']['cardId']
    except Exception:
        # print('Exception',data)
        raise Exception(data)

def findStudentZkNo():
    params = {'paperId': paperId, 'searchKey': ['zkzh AS zkNo']}
    data = requests.post(domain + stuInfoUrl, headers=headers, json=params, verify=False).text
    try:
        result = json.loads(data)

        
        for _zk in result['data']:
            zkList.append(_zk['zkNo'])
    except Exception:
        raise Exception(data)


# 考号填涂, 遍历考号所有字符，找出每个字符对应的坐标填涂
def fillZkNo():
    filterArea('5')
    if len(zkNo) <= len(areas):
        for _i in range(len(zkNo)):
            _j = zkNo[_i]
            area = areas[_i]['area']
            loc = area[int(_j)]
            fillImage(loc)
    else:
        print('考号长度超限', zkNo)


# 客观单选题填涂，随机填涂其中一个
def fillSingleObjQuest():
    filterArea('12')
    for _gp in group:
        singleFill(_gp)


# 客观多选题填涂，填涂0-all
def fillMultiObjQuest():
    filterArea('7')
    for _i in areas:
        _area = _i['area']
        for loc in _area:
            index = random.randint(0, len(_area))
            if index < len(_area) - 1:
                fillImage(loc)


# 客观选做题填涂，目前只支持一个选做组内多选一场景
def fillOptionObjQuest():
    filterArea('10')
    filterList.clear()
    index = 0 if len(group) == 0 else random.randint(0, len(group) - 1)
    for _i in range(len(group)):
        areaGroup = group[_i]
        if index == _i:
            bk = True
            for _f in areaGroup['areas']:
                for loc in _f['area']:
                    if bk:
                        fillImage(loc)
                        bk = False
        else:
            # 记录非选做题
            if areaGroup['bindTh'] is not None:
                bind = json.loads(areaGroup['bindTh'])
                for questNum in bind:
                    filterList.append(questNum)


# 判断题填涂，随机填涂其中一个
def fillTrueFalseQuest():
    filterArea('15')
    for _gp in group:
        singleFill(_gp)

# 主观选做题填涂，随机填涂其中一个
def fillSubOptionQuest():
    filterArea('26')
    for _gp in group:
        singleFill(_gp)


# 坐标区域筛选
def filterArea(areaType):
    group.clear()
    areas.clear()
    for _i in groups:
        if _i['zustyle'] == areaType and _i['questitle'] not in filterList:
            if _i['pageid'] == pageNo + 1:
                group.append(_i)
                for _a in _i['areas']:
                    areas.append(_a)


'''
    答题卡填涂脚本
    此脚本依赖于鲲鹏系统在线生成的答题卡模板数据，基于考试模板编写。脚本通过输入的paperId作为
    参数使用API调用的方式自动关联题卡模板和参考学生考号信息，执行前请确保考试已经创建并且已绑定
    在线题卡。
    必要参数：paperId, token, filePath(图片文件保存目录)。
'''
if __name__ == '__main__':
    examId = '097179264042043100002'
    paperId = '097179264042051000003001'
    # 图片文件保存目录路径格式(windows)
    # path = 'C:\\Users\\mdx12\\Downloads\\display\\'
    path = 'C:\\Users\\mdx12\\Downloads\\display\\'
    tempDir = path + 'temp\\'
    tempImgDir = path + 'tempImg\\'
    # 环境域名
      #domain = 'http://dev.local.yjzhixue.com'
    domain = 'https://test.yjzhixue.com'
    # domain = 'https://www.yjzhixue.com'
    cardIdUrl = '/api/cardmng/inner/findCardInfoByPaperId?paperId='
    getPaperCard ='/api/cardmng/getPaperCard/'+examId+'/'+paperId
    cardInfoUrl = '/api/onlinecard/inner/onlinecard/'
    stuInfoUrl = '/api/cardscan/v2/inner/student/list'
    ossSignUrl = '/api/ossproxy/oss/urlMapSign'
    headers = {'Content-Type': 'application/json;charset=UTF-8',
                'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0ZWE3NDMyMzEyNDIiLCJ1c2VyX2lkIjoiMTMzMTYzMDE0MDc5NTI3MjAwMDY2IiwiYXBwX2NvZGUiOiJwbGF0Zm9ybSIsInVzZXJfbmFtZSI6InRlYTc0MzIzMTI0MiIsIm9yZ19pZCI6IjIxMDE2MjI0NDYzMTk4NTkwMDE1NSIsIm9yZ19uYW1lIjoi6L-Z5Y-q5piv5LiA5Liq5py65p6E5ZCN56ewIiwib3JnX3R5cGUiOjIsInVzZXJfdHlwZSI6ImtwX3NjaG9vbCIsInNjb3BlIjoicGxhdGZvcm0iLCJuYW1lIjoi5p2O6ICB5biIMDgyOCIsImlzX3RpcmllZCI6ZmFsc2UsInRyaWVkX3R5cGUiOjAsInRyaWVkX2VuZF90aW1lIjo0MDkyNDgwMDAwMDAwLCJ0cmllZF9hbGxvd19jb3VudCI6MCwiY29tcGFueV9pZCI6IjIxMDE2MjI0NDYzMTk4NTkwMDE1NSIsImFjY19pZCI6IjEzMzE2MzAxNDA3OTUyNzIwMDA2NiIsImNvbXBhbnlfbmFtZSI6Iui_meWPquaYr-S4gOS4quacuuaehOWQjeensCIsInZlcnNpb25faWQiOjEsIm1vYmlsZSI6IjEzNjcwMDMzNTIxIiwiZXhwIjoxNzkzNDA4NjAzfQ.3pV_WhTQHi1uiGq9zm2Zv5M4oXjWUw8cSGFwLN7llERLwWgEjzhbEayfHxrMHmURqPmOdjBnQGRBlzQuJ5Ne9A'
            #     'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0ZWE3NDMyMzEyNDIiLCJ1c2VyX2lkIjoiMTMzMTYzMDE0MDc5NTI3MjAwMDY2IiwiYXBwX2NvZGUiOiJwbGF0Zm9ybSIsInVzZXJfbmFtZSI6InRlYTc0MzIzMTI0MiIsIm9yZ19pZCI6IjIxMDE2MjI0NDYzMTk4NTkwMDE1NSIsIm9yZ19uYW1lIjoi6L-Z5Y-q5piv5LiA5Liq5py65p6E5ZCN56ewIiwib3JnX3R5cGUiOjIsInVzZXJfdHlwZSI6ImtwX3NjaG9vbCIsInNjb3BlIjoicGxhdGZvcm0iLCJuYW1lIjoi5p2O6ICB5biIMDgyOCIsImlzX3RpcmllZCI6ZmFsc2UsInRyaWVkX3R5cGUiOjAsInRyaWVkX2VuZF90aW1lIjo0MDkyNDgwMDAwMDAwLCJ0cmllZF9hbGxvd19jb3VudCI6MCwiY29tcGFueV9pZCI6IjIxMDE2MjI0NDYzMTk4NTkwMDE1NSIsImFjY19pZCI6IjEzMzE2MzAxNDA3OTUyNzIwMDA2NiIsImNvbXBhbnlfbmFtZSI6Iui_meWPquaYr-S4gOS4quacuuaehOWQjeensCIsInZlcnNpb25faWQiOjEsIm1vYmlsZSI6IjEzNjcwMDMzNTIxIiwiZXhwIjoxNzkzNDMzMjY1fQ.2ZeOnYLAGv3XFep73uD30MsfxYD_nwA2a1ksmEXHh1o-kK_ney_8TPywCZJD5SWtf7uwmB-zu521ALjM1rBUog' 
               }

    zkList = []
    groups = []
    areas = []
    group = []
    filterList = []
    markDir(tempImgDir)
    cardId = findCardId()
    findTemp()
    findStudentZkNo()
    tempList = sorted(os.listdir(tempDir))
    for z in range(len(zkList)):
        zkNo = zkList[z]
        if zkNo is not None and len(zkNo) > 0:
            for pageNo in range(len(tempList)):
                print('tempDir + tempList[pageNo]',tempDir + tempList[pageNo])
                img = Image.open(tempDir + tempList[pageNo])
                draw = ImageDraw.Draw(img)
                if pageNo % 2 == 0:
                    
                    fillZkNo()
                fillOptionObjQuest()
                fillMultiObjQuest()
                fillSingleObjQuest()
                fillTrueFalseQuest()
                fillSubOptionQuest()
                img.save(tempImgDir + str(z + 1).zfill(3) + str(pageNo + 1).zfill(2) + '.jpg')
        print('进度 =>', str(z + 1) + '/' + str(len(zkList)))
