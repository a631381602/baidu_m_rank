#coding:utf-8
'''
百度移动排名查询，跑出前两页的domain存入‘serp_html.csv’中
'''
import StringIO,pycurl,time,random,re,os,csv,urllib
from threading import Thread,Lock
from Queue import Queue
from bs4 import BeautifulSoup as bs

csvfile = open('serp_html.csv','wb')    #存放关键词和搜索结果页源码的文件
bdjd_dict = {}
daili_list = [] #存储代理ip

'''随机提取代理ip'''
def ip():
    for x in open('hege_daili.txt'):
        x = x.strip()
        daili_list.append(x)
    newip = random.choice(daili_list)
    return newip

'''若代理ip超过10次连接失败，则从代理ip文件中删除'''
def daili_delete(ip):
    dailifile = open('daili_beifen.txt','w')
    for line in open('hege_daili.txt'):
        line = line.strip()
        if ip not in line:
            dailifile.write(line+"\n")
    os.system("mv daili_beifen.txt hege_daili.txt")

#定义UA
def getUA():
    uaList = ['Mozilla/4.0+(compatible;+MSIE+6.0;+Windows+NT+5.1;+SV1;+.NET+CLR+1.1.4322;+TencentTraveler)',
    'Mozilla/4.0+(compatible;+MSIE+6.0;+Windows+NT+5.1;+SV1;+.NET+CLR+2.0.50727;+.NET+CLR+3.0.4506.2152;+.NET+CLR+3.5.30729)',
    'Mozilla/5.0+(Windows+NT+5.1)+AppleWebKit/537.1+(KHTML,+like+Gecko)+Chrome/21.0.1180.89+Safari/537.1',
    'Mozilla/4.0+(compatible;+MSIE+6.0;+Windows+NT+5.1;+SV1)',
    'Mozilla/5.0+(Windows+NT+6.1;+rv:11.0)+Gecko/20100101+Firefox/11.0',
    'Mozilla/4.0+(compatible;+MSIE+8.0;+Windows+NT+5.1;+Trident/4.0;+SV1)',
    'Mozilla/4.0+(compatible;+MSIE+8.0;+Windows+NT+5.1;+Trident/4.0;+GTB7.1;+.NET+CLR+2.0.50727)',
    'Mozilla/4.0+(compatible;+MSIE+8.0;+Windows+NT+5.1;+Trident/4.0;+KB974489)',
    'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36',
    'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36'
    ]
    headers = random.choice(uaList)
    return headers

#随机抽取百度节点
def getBDJD(bdjd_str):
    bdjd_list = bdjd_str.split(',')
    bdjd = random.choice(bdjd_list)
    return bdjd

'''
获取百度源码，若要使用代理，则需引入ip参数，即 is_index(url,headers,ip) ，并取消 c.setopt(c.PROXY,ip) #号的注释
'''
def is_index(url,headers):
    while 1:
        try:
            c = pycurl.Curl()
            c.setopt(pycurl.MAXREDIRS,5)
            c.setopt(pycurl.REFERER, url)
            c.setopt(pycurl.FOLLOWLOCATION, True)
            c.setopt(pycurl.CONNECTTIMEOUT, 120)
            c.setopt(pycurl.TIMEOUT,120)
            c.setopt(pycurl.ENCODING,'gzip,deflate')
            #c.setopt(c.PROXY,ip)       '''若使用代理，则取消本行注释'''
            c.fp = StringIO.StringIO()
            c.setopt(pycurl.URL, url)
            c.setopt(pycurl.HTTPHEADER,headers)
            c.setopt(c.WRITEFUNCTION, c.fp.write)
            c.perform()
            #code = c.getinfo(c.HTTP_CODE) 返回状态码
            html = c.fp.getvalue()
            if '="http://verify.baidu.com' in html:
                print '出验证码,暂停10分钟'
                time.sleep(100)
                continue
            else:
                return html
        except Exception, what:
            information = '错误信息：%s' % what
            return str(information)
            continue
             

#正则提取模块
def search(req,line):
    text = re.search(req,line)
    if text:
        data = text.group(1)
    else:
        data = 'no'
    return data

'''需要查询排名的关键词传入url_list，关键词存放在word中，一行一个'''
url_list = []   
for line in open('word'):
    word = line.strip()
    url_list.append(word)

'''多线程抓取函数'''
class Fetcher:
    def __init__(self,threads):
        self.lock = Lock() #线程锁
        self.q_req = Queue() #任务队列
        self.q_ans = Queue() #完成队列
        self.threads = threads
        for i in range(threads):
            t = Thread(target=self.threadget) #括号中的是每次线程要执行的任务
            t.setDaemon(True) #设置子线程是否随主线程一起结束，必须在start()
                              #之前调用。默认为False
            t.start() #启动线程
        self.running = 0 #设置运行中的线程个数
 
    def __del__(self): #解构时需等待两个队列完成
        time.sleep(0.5)
        self.q_req.join() #Queue等待队列为空后再执行其他操作
        self.q_ans.join()
 
    #返回还在运行线程的个数，为0时表示全部运行完毕
    def taskleft(self):
        return self.q_req.qsize()+self.q_ans.qsize()+self.running 

    def push(self,req):
        self.q_req.put(req)
 
    def pop(self):
        return self.q_ans.get()
 
    #线程执行的任务，根据req来区分 
    def threadget(self):
        while True:
            line = self.q_req.get()
            word = line.strip()

            '''
            Lock.lock()操作，使用with可以不用显示调用acquire和release，
            这里锁住线程，使得self.running加1表示运行中的线程加1，
            如此做防止其他线程修改该值，造成混乱。
            with下的语句结束后自动解锁。
            '''

            with self.lock: 
                self.running += 1

            '''构造请求头，header请自行修改'''
            headers = [
                "ccept:application/json",
                "Accept-Encoding:gzip, deflate, sdch",
                "Accept-Language:zh-CN,zh;q=0.8,en;q=0.6",
                "Connection:keep-alive",
                "Cookie:BDUSS=FM3cjJ5NElmMTB4UFMzcjBjakYzRGtmYkc0Y08za2pETDl2dVJOYmNXSE5tTkZWQVFBQUFBJCQAAAAAAAAAAAEAAADLTBsKYTYzMTM4MTcwMgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAM0LqlXNC6pVV; MSA_WH=1436_369; SIGNIN_UC=70a2711cf1d3d9b1a82d2f87d633bd8a01879750777; lsv=e3a825ec2e6e44091; BDRCVFR[ltbVPlNi2ac]=mk3SLVN4HKm; plus_lsv=bdecac14975cf366; PLUS=1; BDICON=10123156; BAIDUID=4B0DC2F54860625BA83681F98C507951:SL=0:NR=10:FG=1; btm=1",
                "Host:m.baidu.com",
                "RA-Sid:7739A016-20140918-030243-3adabf-48f828",
                "RA-Ver:3.0.7",
                "Referer:http://m.baidu.com/",
                "User-Agent:Mozilla/5.0 (iPhone; CPU iPhone OS 5_0 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A334 Safari/7534.48.3",
                "X-Requested-With:XMLHttpRequest"
            ]    

            #newip = ip()   '''若使用代理，则取消本行注释'''
            #bdjd = getBDJD(bdjd_str)   '''若使用百度节点，则取消本行注释，并在构造url时引入bdjd'''
            url1 = 'http://m.baidu.com/s?sa=np&wpo=base&at=1&tn=iphone&word=%s&usm=1&pn=0' % urllib.quote_plus(word)
            url2 = 'http://m.baidu.com/s?sa=np&wpo=base&at=1&tn=iphone&word=%s&usm=1&pn=10' % urllib.quote_plus(word)

            html_one = eval(is_index(url1,headers))
            for id in range(1,11):
                key = 'Results_www_%s' % id
                text = html_one[key].replace('\/','/')
                domain = search(r'class="site">(.*?)</span>',text)
                if domain == 'no':
                    domain = search(r'(\w+\.\w+\.\w+)\s\d+k',text)
                rank = id
                lading = urllib.unquote(search(r'data-url="([^"]*?)"',text))

                data = []
                data.append(word)
                data.append(rank)
                data.append(domain)
                data.append(lading)
                writer = csv.writer(csvfile,dialect='excel')
                writer.writerow(data)

            html_two = eval(is_index(url2,headers))
            for id in range(1,11):
                key = 'Results_www_%s' % id
                text = html_two[key].replace('\/','/')
                domain = search(r'class="site">(.*?)</span>',text)
                if domain == 'no':
                    domain = search(r'(\w+\.\w+\.\w+)\s\d+k',text)
                rank = id + 10
                lading = urllib.unquote(search(r'data-url="([^"]*?)"',text))

            
                data = []
                data.append(word)
                data.append(rank)
                data.append(domain)
                data.append(lading)
                writer = csv.writer(csvfile,dialect='excel')
                writer.writerow(data)

            time.sleep(3)

            print '已查询：%s' % word
            #self.q_ans.put((req,ans)) # 将完成的任务压入完成队列，在主程序中返回
            self.q_ans.put(word)
            with self.lock:
                self.running -= 1
            self.q_req.task_done() # 在完成一项工作之后，Queue.task_done()
                                   # 函数向任务已经完成的队列发送一个信号
            time.sleep(0.1) # don't spam
 
if __name__ == "__main__":
    f = Fetcher(threads=10) #设置线程数为10
    for url in url_list:
        f.push(url)         #所有url推入下载队列
    while f.taskleft():     #若还有未完成的的线程
        f.pop()   #从下载完成的队列中取出结果
          








# csvfile = open('serp_html.csv','wb')    #存放关键词和搜索结果页源码的文件
# bdjd_dict = {}

# #bdjd_list = ["www.baidu.com","180.97.33.107","115.239.210.27","180.97.33.108","180.97.33.107","180.97.33.107","180.97.33.108","220.181.111.188","220.181.111.188","180.97.33.107","180.97.33.107","115.239.211.112","180.97.33.108","180.97.33.108","180.97.33.108","180.97.33.108","180.97.33.108","115.239.211.112","180.97.33.108","115.239.211.112","115.239.210.27","180.97.33.108","115.239.211.112","115.239.210.27","180.97.33.108","115.239.210.27","61.135.169.125","115.239.211.112","115.239.210.27","180.97.33.107","180.97.33.107","180.97.33.108","115.239.210.27","180.97.33.107","61.135.169.121","115.239.210.27","61.135.169.121","61.135.169.125","115.239.211.112","115.239.210.27","61.135.169.125","112.80.248.73","61.135.169.121","112.80.248.74","112.80.248.73","61.135.169.125","180.97.33.108","115.239.210.27","61.135.169.125","61.135.169.125","112.80.248.74","112.80.248.74","61.135.169.121","115.239.210.27","61.135.169.125","111.13.100.92","111.13.100.92","111.13.100.91","111.13.100.91","115.239.211.112","111.13.100.92","111.13.100.91","111.13.100.92","115.239.211.112","115.239.210.27","115.239.211.112","115.239.210.27","115.239.210.27","115.239.210.27","115.239.210.27"]
# bdjd_list = ["www.baidu.com"]

# #提取百度地域节点
# def getBDJD(bdjd_str):
#     bdjd_list = bdjd_str.split(',')
#     bdjd = random.choice(bdjd_list)
#     return bdjd



# daili_list = [] #存储代理ip
# #读取代理文件，随机提取1个代理
# def ip():
#     for x in open('hege_daili.txt'):    
#         x = x.strip()
#         daili_list.append(x)
#     newip = random.choice(daili_list)
#     return newip

# #如果代理不可用，则从代理文件中删除，此函数在baidu_cout中应用
# def daili_delete(ip):
#     dailifile = open('daili_beifen.txt','w')
#     for line in open('hege_daili.txt'):
#         line = line.strip()
#         if ip not in line:
#             dailifile.write(line+"\n")
#     os.system("mv daili_beifen.txt hege_daili.txt")

# def baidu_url(word):  #百度搜索url
#     return 'http://www.baidu.com/s?wd=%s' % word

# def getUA():
#     uaList = [
#     'Mozilla/4.0+(compatible;+MSIE+6.0;+Windows+NT+5.1;+SV1;+.NET+CLR+1.1.4322;+TencentTraveler)',
#     'Mozilla/4.0+(compatible;+MSIE+6.0;+Windows+NT+5.1;+SV1;+.NET+CLR+2.0.50727;+.NET+CLR+3.0.4506.2152;+.NET+CLR+3.5.30729)',
#     'Mozilla/5.0+(Windows+NT+5.1)+AppleWebKit/537.1+(KHTML,+like+Gecko)+Chrome/21.0.1180.89+Safari/537.1',
#     'Mozilla/4.0+(compatible;+MSIE+6.0;+Windows+NT+5.1;+SV1)',
#     'Mozilla/5.0+(Windows+NT+6.1;+rv:11.0)+Gecko/20100101+Firefox/11.0',
#     'Mozilla/4.0+(compatible;+MSIE+8.0;+Windows+NT+5.1;+Trident/4.0;+SV1)',
#     'Mozilla/4.0+(compatible;+MSIE+8.0;+Windows+NT+5.1;+Trident/4.0;+GTB7.1;+.NET+CLR+2.0.50727)',
#     'Mozilla/4.0+(compatible;+MSIE+8.0;+Windows+NT+5.1;+Trident/4.0;+KB974489)',
#     'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36',
#     'Mozilla/5.0 (Windows NT 5.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36'
#     ]
#     ua = random.choice(uaList)
#     return ua

# def baidu_cont(url,headers,ip):  #百度搜索结果页源码
#     while 1:
#         try:
#             c = pycurl.Curl()
#             c.setopt(pycurl.MAXREDIRS,5)
#             c.setopt(pycurl.REFERER, url)
#             c.setopt(pycurl.FOLLOWLOCATION, True)
#             c.setopt(pycurl.CONNECTTIMEOUT, 60)
#             c.setopt(pycurl.TIMEOUT,120)
#             c.setopt(pycurl.ENCODING,'gzip,deflate')
#             c.setopt(c.PROXY,ip)
#             c.fp = StringIO.StringIO()
#             c.setopt(pycurl.URL, url)
#             c.setopt(pycurl.HTTPHEADER,headers)
#             c.setopt(c.WRITEFUNCTION, c.fp.write)
#             c.perform()
#             #code = c.getinfo(c.HTTP_CODE) 返回状态码
#             html = c.fp.getvalue()

#             if '="http://verify.baidu.com' in html:
#                 time.sleep(1200)
#                 print '重启'
#                 continue
#             return html
#         except Exception, what:
#             information = '错误信息：%s' % what
#             return str(information)
#             continue

# def search(req,line):
#     text = re.search(req,line)
#     if text:
#         data = text.group(1)
#     else:
#         data = 'no'
#     return data

# url_list = []
# for word in open('word'):
#     word = word.strip()
#     url_list.append(word)

# class Fetcher:
#     def __init__(self,threads):
#         self.lock = Lock() #线程锁
#         self.q_req = Queue() #任务队列
#         self.q_ans = Queue() #完成队列
#         self.threads = threads
#         for i in range(threads):
#             t = Thread(target=self.threadget) #括号中的是每次线程要执行的任务
#             t.setDaemon(True) #设置子线程是否随主线程一起结束，必须在start()
#                               #之前调用。默认为False
#             t.start() #启动线程
#         self.running = 0 #设置运行中的线程个数
 
#     def __del__(self): #解构时需等待两个队列完成
#         time.sleep(0.5)
#         self.q_req.join() #Queue等待队列为空后再执行其他操作
#         self.q_ans.join()
 
#     #返回还在运行线程的个数，为0时表示全部运行完毕
#     def taskleft(self):
#         return self.q_req.qsize()+self.q_ans.qsize()+self.running 

#     def push(self,req):
#         self.q_req.put(req)
 
#     def pop(self):
#         return self.q_ans.get()
 
# 	#线程执行的任务，根据req来区分 
#     def threadget(self):
#         while True:
#             line = self.q_req.get()
#             word = line.strip()

#             '''
#             Lock.lock()操作，使用with可以不用显示调用acquire和release，
#             这里锁住线程，使得self.running加1表示运行中的线程加1，
#             如此做防止其他线程修改该值，造成混乱。
#             with下的语句结束后自动解锁。
#             '''

#             with self.lock: 
#                 self.running += 1     

#             bdjd_str = ','.join(bdjd_list)
#             newip = ip()
#             bdjd = getBDJD(bdjd_str)
#             url = baidu_url(word)

#             headers = [
#                 "Accept:text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
#                 "Accept-Encoding:gzip, deflate, sdch",
#                 "Accept-Language:zh-CN,zh;q=0.8,en;q=0.6",
#                 "Cache-Control:max-age=0",
#                 "Connection:keep-alive",
#                 #Cookie:BAIDUID=4472AF5EE177FDE343F595ED23D7EF2D:FG=1; BIDUPSID=4472AF5EE177FDE343F595ED23D7EF2D; PSTM=1433729062; ispeed_lsm=0; BDUSS=1VudTZPZGRWVVZJTFlGT0hWODE1NVRxTVY3WGNpcUJldHJNbmlselZBWWpCcDFWQVFBQUFBJCQAAAAAAAAAAAEAAAAJkstJv7TXvMTj1NnM-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACN5dVUjeXVVM; BDSFRCVID=OpusJeCCxG3N_sOlJEvr-lU9tomzvLxREDct3J; H_BDCLCKID_SF=tbkD_C-MfIvhDRTvhCTjh-FSMgTBKI62aKDsQ4bx-hcqEpO9QTbFBntgh-6e0n3RtJ5ChPoEMtQdJMoHQ-bMDUThDNtDt60jfn3tWJTOajrjDbTnMIT8bKCShUFsWbOt-2Q-5hOy3KOF_POOhM6p5RjDhb_8-PRLMjcrXUoN3nOMhpFu-n5jHjoXjNAj3J; BDRCVFR[ltbVPlNi2ac]=mk3SLVN4HKm; BD_HOME=1; BD_UPN=123253; sug=3; sugstore=1; ORIGIN=0; bdime=0; BDRCVFR[feWj1Vr5u3D]=I67x6TjHwwYf0; H_PS_645EC=748aW%2FWsBPv6DUJliRObDTZAHPnxtYugRksf55XQ9IKqXBbOelDYaS%2Fyh%2B6mzJ85gdS%2F; BD_CK_SAM=1; BDSVRTM=95; H_PS_PSSID=1455_14602_14510_14444_12824_14600_12867_14621_14669_10562_14501_12722_14531_14626_14484_14329_11486_13936_8498; __bsi=2141746194871033810_00_0_I_R_96_0303_C02F_N_I_I
#                 "Host:www.baidu.com",
#                 "RA-Sid:7739A016-20140918-030243-3adabf-48f828",
#                 "RA-Ver:2.10.4",
#                 "User-Agent:%s" % getUA()
#                 ]    
#             html = baidu_cont(url, headers, newip)

#             soup = bs(html)
#             b_tags = soup.find_all('div', {'class': 'result c-container '})
#             for line in b_tags:
#                 newline = str(line)
#                 number = search(r'id="(\d+)"',newline)
#                 urldiv = search(r'<span class="g">(.*?)</span>',newline)    #获取源码中domain所在的<span>

#                 data = []
#                 data.append(word)
#                 data.append(newline)
#                 writer = csv.writer(csvfile,dialect='excel')
#                 writer.writerow(data)
#             if len(b_tags) == 0:
#                 print html
#                 print '》》当前IP：%s,已抓取：%s，返回%s条结果，请求地址：%s' % (newip,word,len(b_tags),url)
#             else:
#                 print '》》当前IP：%s,已抓取：%s，返回%s条结果' % (newip,word,len(b_tags))

#             #self.q_ans.put((req,ans)) # 将完成的任务压入完成队列，在主程序中返回
#             self.q_ans.put(word)
#             with self.lock:
#                 self.running -= 1
#             self.q_req.task_done() # 在完成一项工作之后，Queue.task_done()
#                                    # 函数向任务已经完成的队列发送一个信号
#             time.sleep(0.1) # don't spam
 
# if __name__ == "__main__":
#     #links = [ 'http://www.verycd.com/topics/%d/'%i for i in range(5420,5450) ]
#     f = Fetcher(threads=10) #设置线程数为10
#     for url in url_list:
#         f.push(url)         #所有url推入下载队列
#     while f.taskleft():     #若还有未完成的的线程
#         f.pop()   #从下载完成的队列中取出结果



'''
如果百度节点超时次数》10，则从百度节点列表中删除
if '错误信息' in html:
    print html
    if 'Connection refused' in html:
        #判断访问超时的节点存入字典，若该节点已超过10次链接超时，则从节点列表中删除
        if bdjd_dict.has_key(bdjd):
            bdjd_dict[bdjd] += 1
            print '节点：%s，已%s次超时' % (bdjd,bdjd_dict[bdjd])
            if int(bdjd_dict[bdjd]) >= 10:
                bdjd_list.remove(bdjd)
                print "节点：%s 已删除" % bdjd
        else:
            bdjd_dict[bdjd] = 1
    continue
'''


