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
from requests.packages.urllib3.exceptions import InsecureRequestWarning

emails_q = queue.Queue()

def debug(text, conf):
    if conf['debug']:
        print ("[DEBUG] "+str(text))

def read_configurations():
    try:
        conf = json.loads(open('config/discord_grabtokens.json','r').read())
        print ("Configuration loaded! Starting workers!")
        return conf
    except:
        print ("Failed to load discord_register.json")
        sys.exit(1)

def array_to_queue(arr, q):
    for i in arr:
        q.put(i)
    return q

def save_user(api_key, proxy, conf):
    debug("saving user", conf)
    output = open(conf['output_token_file'], 'a')
    output.write(api_key+"\n")
    output.flush()
    output.close()

def get_headers():
    return {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
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


def getToken(email, password, proxy, conf):
    headers = get_headers()
    s = requests.Session()
    print("Logging into acconut: " + email + ".")
    if proxy != None:
        proxies = {
            'http' : 'http://' + proxy,
            'https' : 'https://' + proxy
        }
        s.proxies.update(proxies)
    fingerprint_json = s.get("https://discordapp.com/api/v6/experiments", timeout=conf['timeout'], headers=headers, verify=False).text
    fingerprint = json.loads(fingerprint_json)["fingerprint"]
    debug("Finger print: " + fingerprint, conf)
    xsuperprop = 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzczLjAuMzY4My4xMDMgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjczLjAuMzY4My4xMDMiLCJvc192ZXJzaW9uIjoiMTAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MzU1NDAsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9'
    debug("X-Super-Properties: " + xsuperprop, conf)
    time.sleep(conf['sleepdelay'])
    headers['X-Super-Properties'] = xsuperprop
    headers['X-Fingerprint'] = fingerprint
    payload = {
        'fingerprint': fingerprint,
        'email': email,
        'password': password,
    }
        
    response = s.post('https://discordapp.com/api/v6/auth/login', json=payload, headers=headers, timeout=conf['timeout'], verify=False)
    debug(response.json(), conf)
    print(response.text)        
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
    response = s.get('https://discordapp.com/api/v6/users/@me', headers=headers, timeout=conf['timeout'], verify=False)
    debug(response.json(), conf)
    save_user(api_key, proxy, conf)
    print("Successfully grabbed token from user.")
    return True


def worker(conf):
    debug("worker started", conf)
    proxy = None    
    if conf['use_proxies']:
        email_pwd = emails_q.get()
        emails_q.task_done()
        password = email_pwd.split(":")[0]
        email = email_pwd.split(":")[1]
        if conf['use_proxies']:
            proxy = email_pwd.split(":")[2] + ":" + email_pwd.split(":")[3]
        
        debug("trying to create new account with proxy "+proxy, conf)
    
    if not getToken(email, password, proxy, conf):
        debug("Failed to grab token from user.", conf)
    else:
        print("Successfully grabbed token from user.")
    worker(conf);

def main():
    global emails_q
    print ("Starting")
    conf = read_configurations()
    tx = []
    data = [x.rstrip() for x in open(conf['emails_file'], 'r').readlines()]
    emails = []
    for _ in data:
        password = _.split(':')[2]
        email = _.split(':')[3]
        proxy = _.split(':')[4]
        if len(_.split(':')) == 6:
            proxy += ":" +  _.split(':')[5]
        emails.append(password + ":" + email + ":" + proxy)
    emails_q = array_to_queue(emails, emails_q)
    debug("Starting "+str(conf['nb_threads'])+" threads", conf)
    for i in range(conf['nb_threads']):
        mT = threading.Thread(target=worker, args=(conf, ))
        mT.start()
        tx.append(mT)
    for t in tx:
        t.join()
    print ("Finished")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    main()