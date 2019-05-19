import sys
import re
import recaptcha
import requests
import json
import random
import queue
import threading
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning

proxies_q = queue.Queue()
tokens_q = queue.Queue()

def debug(text, conf):
    if conf['debug']:
        print ("[DEBUG] "+str(text))

def read_configurations():
    try:
        conf = json.loads(open('config/discord_phone_verify.json','r').read())
        print ("Configuration loaded! Starting workers!")
        return conf
    except:
        sys.exit(1)

def array_to_queue(arr, q):
    for i in arr:
        q.put(i)
    return q

def save_user(token, conf):
    print("User verified, saving user!")
    output = open(conf['output_file'], 'a')
    output.write(":".join(
        [token]
        )+"\n")
    output.close()

def get_headers():
    return {
        'user-agent': 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16',
        'Host': 'discordapp.com',
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Content-Type': 'application/json',
        'Referer': 'https://discordapp.com',
        'DNT': '1',
        'Connection': 'keep-alive'
    }

def verify(token, proxy, conf):
    print("Verifying account: " + token + ".")
    headers = get_headers()
    ss = requests.Session()
    if proxy != None:
        proxies = {
            'http' : 'http://' + proxy,
            'https' : 'https://' + proxy
        }
        ss.proxies.update(proxies)
    fingerprint_json = ss.get("https://discordapp.com/api/v6/experiments", timeout=conf['timeout'], headers=headers, verify=False).text
    fingerprint = json.loads(fingerprint_json)["fingerprint"]
    time.sleep(conf['sleepdelay'])
    headers['X-Fingerprint'] = fingerprint
    
    smsResponse = ss.get('http://smspva.com/priemnik.php?metod=get_number&country=' + conf['smspva_region'] + '&service=opt45&apikey=' + conf['smspva_api_key'], timeout=conf['timeout'], verify=False)
    debug(smsResponse.text, conf)
    number = None
    try:
        smsResponsJSON = json.loads(smsResponse.text)
        if smsResponsJSON['response'] == 2:
            print("[SMSPVA] No number found in the region chosen. Will retry in one minute.")
            time.sleep(60)
            return False
        number = smsResponsJSON['CountryCode'] + smsResponsJSON['number']
    except:
        print(smsResponse.text)
        time.sleep(3)
        return False
    
    print("[SMSPVA] Got a number(" + number + ").")
    #xsuperprop = base64.b64encode(json.dumps(headers, separators=",:").encode()).decode()
    xsuperprop = 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzczLjAuMzY4My4xMDMgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjczLjAuMzY4My4xMDMiLCJvc192ZXJzaW9uIjoiMTAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MzU1NDAsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9'
    headers['X-Super-Properties'] = xsuperprop
    time.sleep(2.5)
    
    payload = {
        "phone": number
    }
    headers['Authorization'] = token
    response = ss.post('https://discordapp.com/api/v6/users/@me/phone', headers=headers, json=payload, timeout=conf['timeout'], verify=False)
    valid = False	
    if response.status_code == 204:
        valid = True
    else:
        print(response.json()['message'])
        return False
    
    print("[SMSPVA] Waiting for code...")
    time.sleep(2.5)
    if valid:
        response = None
        maxAttempts = 30
        attempts = 0
        while 1:
            if attempts >= maxAttempts:
                break
            
            time.sleep(20)
            response = ss.get('http://smspva.com/priemnik.php?metod=get_sms&country=' + conf['smspva_region'] + '&service=opt45&id=' + str(smsResponsJSON['id']) + '&apikey=' + conf['smspva_api_key'], timeout=conf['timeout'], verify=False)
            attempts += 1
            
            if json.loads(response.text)['sms'] != None:
                break
        
        if attempts >= maxAttempts:
            ss.get('http://smspva.com/priemnik.php?metod=ban&service=opt45&apikey=' + conf['smspva_api_key'] + '&id=' + str(smsResponsJSON['id']), timeout=conf['timeout'], verify=False)
            return False
        code = json.loads(response.text)['sms']
        debug(response.text, conf)
        print("[SMSPVA] Found code: " + str(code) + ".")
        newPayload = {
            'code': code
        }
        
        lastResponse = ss.post('https://discordapp.com/api/v6/users/@me/phone/verify', headers=headers, json=newPayload, timeout=conf['timeout'], verify=False)
        
        if lastResponse.status_code == 204:
            save_user(token, conf)
            return True
        else:
            debug(lastResponse.text, conf)
            debug(lastResponse.status_code, conf)
            print(json.loads(lastResponse.text)['message'])
            return False

def worker(conf):
    while not tokens_q.empty():
        email_pwd = tokens_q.get()
        tokens_q.task_done()
        token = email_pwd
        proxy = None    
        if conf['use_proxies']:
            proxies_used_file = conf['usedproxies']
            try:
                proxies_used = open(proxies_used_file).read()
            except:
                proxies_used = ''
        
            proxy = proxies_q.get()
            proxies_q.put(proxy)
            proxies_q.task_done()
        
            while proxies_used.count(proxy) > 2:
                proxy = proxies_q.get()
                proxies_q.put(proxy)
                proxies_q.task_done()
        
            open(proxies_used_file,'a').write(proxy+'\n')
        verify(token, proxy, conf)
def main():
    global tokens_q
    global proxies_q
    conf = read_configurations()
    debug("Starting", conf)
    data = [x.rstrip() for x in open(conf['tokens_file'], 'r').readlines()]
    tokens = []
    alreadydone = [x.rstrip() for x in open(conf['output_file'], 'r').readlines()]
    proxies = [x.rstrip() for x in open(conf['proxy_file'], 'r').readlines()]
    proxies_q = array_to_queue(proxies, proxies_q)
    for _ in data:
        token = _
        if token not in alreadydone:
            tokens.append(token)
    tokens_q = array_to_queue(tokens, tokens_q)
    tx = []

    debug("Starting "+str(conf['nb_threads'])+" threads", conf)
    for i in range(conf['nb_threads']):
        mT = threading.Thread(target=worker, args=(conf, ))
        mT.start()
        tx.append(mT)
        time.sleep(3)
    for t in tx:
        t.join()
    
    data = [x.rstrip() for x in open(conf['tokens_file'], 'r').readlines()]
    notDone = False
    alreadydone = [x.rstrip() for x in open(conf['output_file'], 'r').readlines()]
    for _ in data:
        try:
            token = _
            if token not in alreadydone:
                notDone = True
        except:
            pass
    
    if notDone:
        main()
    debug("Finished", conf)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    main()