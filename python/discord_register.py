import sys
import re
import recaptcha
import requests
import json
import random
import queue
import threading
import time
import base64
import os
from requests.packages.urllib3.exceptions import InsecureRequestWarning

proxies_q = queue.Queue()
domains = queue.Queue()
predefinedNames = []
amount = 0
curAmount = 0
def debug(text, conf):
    if conf['debug']:
        print ("[DEBUG] "+str(text))

def read_configurations():
    try:
        conf = json.loads(open('config/discord_register.json','r').read())
        print ("Configuration loaded! Starting workers!")
        return conf
    except:
        print ("Failed to load discord_register.json")
        sys.exit(1)

def array_to_queue(arr, q):
    for i in arr:
        q.put(i)
    return q

def save_user(email, email_apassword, username, password, discriminator, api_key, proxy, conf):
    debug("saving user", conf)
    output = open(conf['output_file'], 'a')
    if proxy != None:
        output.write(":".join(
            [discriminator, username, password, email, email_apassword, proxy]
            )+"\n")
    else:
        output.write(":".join(
            [discriminator, username, password, email, email_apassword]
            )+":None\n")
    output.flush()
    output.close()
    output = open(conf['output_token_file'], 'a')
    output.write(api_key+"\n")
    output.flush()
    output.close()

def generate_user_pass_pair(override, conf):
    starts = ['the','inlovewith_','dislikes_','kisses_','mr', 'dancing', 'swiping' , 'hot', 'killin', 'tricking', 'pirced', 'banana', 'quicky', 'da', 'mrs', 'professional', 'god', 'godess', 'super', 'power', 'big', 'not']
    verbs = ['awkward','thin','thick','happy','sad','tall','short','malious','ravenous','smooth','loving','mean','weird','high','sober',"smart",'dumb','rich','poor','mega','music','lord', 'uber', 'magician', 'insane', 'genius', 'incredible', 'amazin']
    nouns = ['hacker','lumberjack','horse','unicorn','guy','girl','man','woman','male','female','men','women','duck','dog','sheep','zombie','tennis','doctor', 'cattle', 'zombie', 'monster', 'pwner', 'haxor', 'slayer', 'killer', 'fighter', 'destroyer', 'v', 'a','b','c','d']
    random_touch = random.randint(1,1000)
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    pw_length = 12
    mypw = ""
    for i in range(pw_length):
        next_index = random.randrange(len(alphabet))
        mypw = mypw + alphabet[next_index]
    return ((random.choice(starts) + random.choice(verbs) + '_' + random.choice(nouns) + str(random_touch) if not conf['override_names_with_list'] or override else random.choice(predefinedNames)), mypw)

def generateEmail(mail, conf):
    if conf['override_email']:
        return mail + random.choice(conf['email_override'])
    if conf['use_imap']:
        return random.choice(domains)
    return mail + "@" + random.choice(domains)

def generateUUID():
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    uuidlength = 32
    uuid = ""
    for i in range(uuidlength):
        uuid = uuid + alphabet[random.randrange(len(alphabet))]
    return uuid

def getGenericHeader():
    return {
        'Host': 'getinboxes.com',
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Content-Type': 'application/json',
        'DNT': '1',
        'Connection': 'keep-alive'
    }

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
        'Referer': 'https://discordapp.com/register',
        'Origin': 'https://discordapp.com',
        'DNT': '1',
        'Connection': 'keep-alive'
    }

def getSciencePayload(uuid, theType, location):
    curtime = int(time.time() * 1000.0)
    return {
        'events': [
            {
                'properties': {
                    'client_send_timestamp': curtime,
                    'client_track_timestamp': curtime,
                    'client_uuid': uuid,
                    'location': location,
                    'login_source': None,
                },
                'type': theType
            }
        ]
    }

def getSuperProp(os, browser, useragent, browser_version, os_version, client_build):
    return {
        "os": os,
        "browser": browser,
        "device": "",
        "browser_user_agent": useragent,
        "browser_version": browser_version,
        "os_version": os_version,
        "referrer": "",
        "referring_domain": "",
        "referrer_current": "",
        "referring_domain_current": "",
        "release_channel": "stable",
        "client_build_number": client_build,
        "client_event_source": None
    }

def getRandomPicture(conf):
    files = os.listdir(conf['profilepicturedir'])
    with open(conf['profilepicturedir'] + "/" + files[random.randrange(0, len(files))], "rb") as pic:
        return "data:image/png;base64," + base64.b64encode(pic.read()).decode('utf-8')

def register(email, epass, proxy, conf):
    headers = get_headers()
    genericHeaders = getGenericHeader()
    os, browser, headers['user-agent'], browserver, osvers = getInfo()
    genericHeaders['user-agent'] = headers['user-agent']
    s = requests.Session()
    print("Creating new account...")
    if proxy != None:
        proxies = {
            'http' : 'http://' + proxy,
            'https' : 'https://' + proxy
        }
        s.proxies.update(proxies)
    if not conf['use_imap']: 
        s.get('https://getinboxes.com/api/v1/u/' + email + '/' + str(int(time.time() * 1000.0)), headers=genericHeaders, verify=False)
        time.sleep(conf['sleepdelay'])
        s.get('https://getinboxes.com/api/v1/inboxes/' + email, headers=genericHeaders, verify=False)
        time.sleep(conf['sleepdelay'])
    fingerprint_json = s.get("https://discordapp.com/api/v6/experiments", timeout=conf['timeout'], headers=headers, verify=False).text
    fingerprint = json.loads(fingerprint_json)["fingerprint"]
    debug("Finger print: " + fingerprint, conf)
    xsuperprop = base64.b64encode(json.dumps(getSuperProp(os, browser, headers['user-agent'], browserver, osvers, 36127), separators=",:").encode()).decode()
    debug("X-Super-Properties: " + xsuperprop, conf)
    time.sleep(conf['sleepdelay'])
    headers['X-Super-Properties'] = xsuperprop
    headers['X-Fingerprint'] = fingerprint
    (username, password) = generate_user_pass_pair(False, conf)
    payload = {
        'fingerprint': fingerprint,
        'email': email,
        'username': username,
        'password': password,
        'invite': None,
        'captcha_key': None,
        'consent': True,
        'gift_code_sku_id': None
    }
    uuid = generateUUID()
    #time.sleep(conf['sleepdelay'])
    #s.post("https://discordapp.com/api/v6/science", timeout=conf['timeout'], json=getSciencePayload(uuid, "login_viewed", "Non-Invite Login Page"), headers=headers, verify=False)
    #time.sleep(conf['sleepdelay'])
    #s.get("https://discordapp.com/api/v6/auth/consent-required", timeout=conf['timeout'], headers=headers, verify=False)
    #time.sleep(conf['sleepdelay'])
    #s.post("https://discordapp.com/api/v6/science", timeout=conf['timeout'], json=getSciencePayload(uuid, "register_viewed", "Non-Invite Register Page"), headers=headers, verify=False)
    
    debug("first registration post "+email+":"+username+":"+password, conf)
    response = s.post('https://discordapp.com/api/v6/auth/register', json=payload, headers=headers, timeout=conf['timeout'], verify=False)
    time.sleep(conf['sleepdelay'])
    captchaRequired = False
    if 'captcha-required' in response.text:
        print("Captcha is required to verify user.")
        captchaRequired = True
    if 'You are being rate limited.' in response.text:
        print("You are being rate limited.")
        return False
    if 'Email is already registered.' in response.text:
        print("Already registered")
        return False
    if 'Please update Discord to continue.' in response.text:
        print("Please update Discord to continue.")
        return False
    if 'response-already-used-error' in response.text:
        print("Captcha response already used once. Returning.")
        return False
    
    if captchaRequired:
        if conf['skip_if_captcha']:
            return False
    
        time.sleep(conf['sleepdelay'])
        debug("fetching captcha", conf)
        captchaResult = recaptcha.GetCaptcha(None, proxy).split("|")
        captcha = captchaResult[0]
        captchaId = captchaResult[1]
        debug("Result: "+captcha, conf)
        payload['captcha_key'] = captcha
        debug("sending payload: "+str(payload), conf)
        time.sleep(conf['sleepdelay'])
        response = s.post('https://discordapp.com/api/v6/auth/register', json=payload, headers=headers, timeout=conf['timeout'], verify=False)
        debug(response.json(), conf)
        if 'incorrect-captcha-sol' in response.text:
            recaptcha.reportCaptcha(captchaId, "bad")
            return False
        elif 'response-already-used-error' in response.text:
            print("Captcha response already used once. Returning.")
            return False
        else:
            recaptcha.reportCaptcha(captchaId, "good")
        
    if 'unauthorize' in response.text:
        debug('unauthorized', conf)
        return False
    try:
        api_key = response.json()['token']
    except:
        return False
    headers['Authorization'] = api_key
    debug("login in and fetching token/api key", conf)
    time.sleep(conf['sleepdelay'])
    
    imagePayload = {
        'avatar': getRandomPicture(conf)
    }
    
    response = s.patch('https://discordapp.com/api/v6/users/@me', json=imagePayload, headers=headers, timeout=conf['timeout'], verify=False)
    if not 'discriminator' in response.json():
        time.sleep(conf['sleepdelay'])
        response = s.get('https://discordapp.com/api/v6/users/@me', headers=headers, timeout=conf['timeout'], verify=False)
        print("Failed to set a profile picture, account possibly needing verification or faulty proxy.")
    if not 'discriminator' in response.json():
        print("Failed to grab discriminator, account invalid? Skipping.")
    debug(response.json(), conf)
    discriminator = response.json()['discriminator']
    save_user(email, epass, username, password, discriminator, api_key, proxy, conf)
    return True


def worker(conf):
    global curAmount
    global amount
    debug("worker started", conf)
    proxy = None    
    if conf['use_proxies']:
        proxies_used_file = conf['usedproxies']
        try:
            proxies_used = open(proxies_used_file).read()
        except:
            proxies_used = ''
    
        proxy = proxies_q.get()
        proxies_q.task_done()
    
        while proxies_used.count(proxy) > 2 and not proxies_q.empty():
            proxy = proxies_q.get()
            proxies_q.task_done()
        open(proxies_used_file,'a').write(proxy+'\n')
    (email, unneededpw) = generate_user_pass_pair(True, conf)
    email = generateEmail(email.lower(), conf)
    if conf['use_imap']:
        mails_used_file = conf['use_imap_mail_used']
        try:
            mails_used = open(mails_used_file).read()
        except:
            mails_used = ''
    
        email = domains.get()
        domains.task_done()
    
        while mails_used.count(email.split(":")[0]) > 0 and not domains.empty():
            email = domains.get()
            domains.task_done()
        unneededpw = email.split(":")[1]
        email = email.split(":")[0]
    
    if(curAmount >= amount and amount != -1):
        return
    if(amount != -1):
        curAmount += 1
    try:
        if not register(email, unneededpw, proxy, conf):
            print("Failed to register user.")
            if amount == -1:
                worker(conf)
            if(curAmount >= amount and amount != -1):
                curAmount -= 1
                worker(conf)
        else:
            open(conf['use_imap_mail_used'],'a').write(email+'\n')
            print("Successfully made a account.")
            open(proxies_used_file,'a').write(proxy+'\n')
            if amount == -1:
                worker(conf)
            if(curAmount < amount and amount != -1):
                worker(conf)
    except:
        if(curAmount < amount):
            worker(conf)
        pass

def runIt(conf):
    tx = []
    debug("Starting "+str(conf['nb_threads'])+" threads", conf)
    for i in range(conf['nb_threads']):
        mT = threading.Thread(target=worker, args=(conf, ))
        mT.daemon = True
        mT.start()
        tx.append(mT)
    for t in tx:
        t.join(75)


def main():
    global proxies_q
    global domains
    global predefinedNames
    global amount
    if(amount != -1):
        amount = int(input("Please enter a estimate of amount of accounts wanted to be created(or -1 for no limit): "))
    print ("Starting")
    conf = read_configurations()
    proxies = [x.rstrip() for x in open(conf['proxy_file'], 'r').readlines()]
    proxies_q = array_to_queue(proxies, proxies_q)
    predefinedNames = [x.rstrip() for x in open(conf['override_names_list'], 'r').readlines()]
    print ("Fetching domain list...")
    s = requests.Session()
    domains_arr = []
    if not conf['override_email']:
        response = s.get('https://getinboxes.com/api/v1/domains', headers=getGenericHeader(), verify=False)
        jsonObj = json.loads(response.text)
        blacklisted = [x.rstrip() for x in open(conf['blacklist_emails'], 'r').readlines()]
        for entry in jsonObj:
            if entry['state'] == 'active' and entry['name'] not in blacklisted:
                domains_arr.append(entry['name'])
        domains = domains_arr
    elif conf['override_email']:
        domains_arr = conf['email_override']
        domains = array_to_queue(domains_arr, domains)
    if conf['use_imap']: 
        domains_arr = [x.rstrip() for x in open(conf['use_imap_mail_in'], 'r').readlines()]
        domains = array_to_queue(domains_arr, domains)
    print ("Domains found:", domains_arr)
    debug("Starting "+str(conf['nb_threads'])+" threads", conf)
    
    if(amount == -1):
        while True:
            runIt(conf)
    else:
        runIt(conf)
    print ("Finished")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    main()