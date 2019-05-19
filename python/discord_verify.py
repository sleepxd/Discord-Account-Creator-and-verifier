import sys
import re
import recaptcha
import requests
import json
import random
import queue
import threading
import time
import imaplib
import email
import email.header
from requests.packages.urllib3.exceptions import InsecureRequestWarning
emails_q = queue.Queue()

def debug(text, conf):
    if conf['debug']:
        print ("[DEBUG] "+str(text))

def read_configurations():
    try:
        conf = json.loads(open('config/discord_verify.json','r').read())
        print ("Configuration loaded! Starting workers!")
        return conf
    except:
        sys.exit(1)

def array_to_queue(arr, q):
    for i in arr:
        q.put(i)
    return q

def save_user(email, conf):
    print("User verified, saving user!")
    output = open(conf['output_file'], 'a')
    output.write(":".join(
        [email]
        )+"\n")
    output.close()

def getInfo():
    id = random.randint(1, 7)
    if id == 1:
        return ("Windows", "Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36", "69.0.3497.100", "10")
    elif id == 2:
        return ("Windows", "Chrome", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/18.17763", "18.17763", "10")
    elif id == 3:
        return ("Windows", "Edge", "Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36", "60.0.3112.90", "XP")
    elif id == 4:
        return ("Windows", "Chrome", "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36", "60.0.3112.113", "8.1")
    elif id == 5:
        return ("Windows", "Internet Explorer", "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; .NET4.0C; .NET4.0E; .NET CLR 2.0.50727; .NET CLR 3.0.30729; .NET CLR 3.5.30729; rv:11.0) like Gecko", "11.0", "7")
    elif id == 6:
        return ("Windows", "Firefox", "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0", "54.0", "7")
    elif id == 7:
        return ("Windows", "Firefox", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0", "66.0", "10")

def get_headers():
    return {
        'Host': 'discordapp.com',
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Content-Type': 'application/json',
        'Referer': 'https://discordapp.com',
        'DNT': '1',
        'Connection': 'keep-alive'
    }

def getGenericHeader():
    return {
        'Host': 'getinboxes.com',
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Content-Type': 'application/json',
        'DNT': '1',
        'Connection': 'keep-alive'
    }

def verify(theemail, epass, proxy, conf):
    print("Verifying account: " + theemail + ".")
    headers = get_headers()
    genericHeaders = getGenericHeader()
    os, browser, headers['user-agent'], browserver, osvers = getInfo()
    genericHeaders['user-agent'] = headers['user-agent']
    ss = requests.Session()
    if proxy != None:
        proxies = {
            'http' : 'http://' + proxy,
            'https' : 'https://' + proxy
        }
        ss.proxies.update(proxies)
        debug("Testing proxy: " + proxy , conf)
    
    debug("opening email", conf)
    activation = None
    if not conf['use_imap']:
        response = ss.get('https://getinboxes.com/api/v1/inboxes/' + theemail, verify=False)
        text = response.text
        time.sleep(conf['sleepdelay'])
        debug("trying to find link", conf)
        if text == "[]":
            ss.get('https://getinboxes.com/api/v1/u/' + theemail + '/' + str(int(time.time() * 1000.0)), headers=genericHeaders, verify=False)
            time.sleep(conf['sleepdelay'])
            ss.get('https://getinboxes.com/api/v1/inboxes/' + theemail, headers=genericHeaders, verify=False)
            time.sleep(conf['sleepdelay'])
            print("Found no mail, maybee try the resend script?")
            return False
        theJson = json.loads(text)[0]
        link = 'https://getinboxes.com/api/v1/messages/html/' + theJson['uid']
        debug("found email link: "+link, conf)
        time.sleep(conf['sleepdelay'])
        response = ss.get(link, verify=False).text
        activation = re.search(r'\s*([\"\'(])((?:https://discordapp\.com/verify|\/).*?)\1[>\s]|\(((?:https://discordapp\.com/verify|\/).*?)\)[>\s]', response).group(0)[1:-2]
    else:
        imap = imaplib.IMAP4_SSL(conf['imap_host'], conf['imap_port'])
        rv, data = imap.login(theemail, epass)
        rv, data = imap.select("INBOX")
        rv, data = imap.search(None, "ALL")
        for num in data[0].split():
            rv, data = imap.fetch(num, '(RFC822)')
            if rv != 'OK':
                continue
            
            message = email.message_from_bytes(data[0][1])
            header = email.header.make_header(email.header.decode_header(message['Subject']))
            subject = str(header)
            if "Verify Email Address for Discord" not in subject:
                continue
            
            activation = re.search(r'(?P<url>https?://discordapp\.com/verify\?token=[^\s]+)', str(message)).group(0)
            break
        
    debug("found activation link: "+activation, conf)
    token = activation.split("?token=")[1]
    debug("token is "+token, conf)
    debug("opening activation link", conf)
    time.sleep(conf['sleepdelay'])
    payload = {
        'token' : token
    }
    time.sleep(conf['sleepdelay'])
    fingerprint_json = ss.get("https://discordapp.com/api/v6/experiments", timeout=conf['timeout'], headers=headers, verify=False).text
    fingerprint = json.loads(fingerprint_json)["fingerprint"]
    debug("Finger print: " + fingerprint, conf)
    time.sleep(conf['sleepdelay'])
    headers['X-Fingerprint'] = fingerprint
    
    newresponse = ss.post('https://discordapp.com/api/v6/auth/verify', json=payload, headers=headers, timeout=conf['timeout'], verify=False)
    captchaRequired = False
    if 'captcha-required' in newresponse.text:
        print("Captcha is required to verify user.")
        captchaRequired = True
    if 'You are being rate limited.' in newresponse.text:
        print("You are being rate limited.")
        return False
    
    if captchaRequired:
        time.sleep(conf['sleepdelay'])
        captchaResult = recaptcha.GetCaptcha(None, proxy).split("|")
        captcha = captchaResult[0]
        captchaId = captchaResult[1]
        debug("fetching a captcha", conf)
        payload['captcha_key'] = captcha
        debug("sending payload:"+str(payload), conf)
        newresponse = ss.post('https://discordapp.com/api/v6/auth/verify', json=payload, headers=headers, timeout=conf['timeout'], verify=False)
        debug(newresponse.text, conf)
        if 'incorrect-captcha-sol' in newresponse.text:
            recaptcha.reportCaptcha(captchaId, "bad")
            return False
        elif 'response-already-used-error' in newresponse.text:
            print("Captcha response already used once. Returning.")
            return False
        else:
            recaptcha.reportCaptcha(captchaId, "good")
    save_user(theemail, conf)
    return True

def worker(conf):
    while not emails_q.empty():
        email_pwd = emails_q.get()
        emails_q.task_done()
        email = email_pwd.split(":")[0]
        epass = email_pwd.split(":")[1]
        proxy = None
        if conf['use_proxies']:
            proxy = email_pwd.split(":")[2] + ":" + email_pwd.split(":")[3]
        verify(email.lower(), epass, proxy, conf)

def main():
    global emails_q
    conf = read_configurations()
    debug("Starting", conf)
    data = [x.rstrip() for x in open(conf['emails_file'], 'r').readlines()]
    emails = []
    alreadydone = [x.rstrip() for x in open(conf['output_file'], 'r').readlines()]
    for _ in data:
        email = _.split(':')[3]
        epass = _.split(':')[4]
        proxy = _.split(':')[5]
        if len(_.split(':')) == 7:
            proxy += ":" +  _.split(':')[6]
        if email not in alreadydone:
            emails.append(email + ":" + epass + ":" + proxy)
    emails_q = array_to_queue(emails, emails_q)
    tx = []
    debug("Starting "+str(conf['nb_threads'])+" threads", conf)
    for i in range(conf['nb_threads']):
        mT = threading.Thread(target=worker, args=(conf, ))
        mT.start()
        tx.append(mT)
    for t in tx:
        t.join()
    
    data = [x.rstrip() for x in open(conf['emails_file'], 'r').readlines()]
    notDone = False
    alreadydone = [x.rstrip() for x in open(conf['output_file'], 'r').readlines()]
    for _ in data:
        try:
            email = _.split(':')[3]
            if email not in alreadydone:
                notDone = True
        except:
            pass
    
    if notDone:
        main()
    debug("Finished", conf)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    main()