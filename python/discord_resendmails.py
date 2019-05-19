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

tokens_q = queue.Queue()
proxies_q = queue.Queue()

def debug(text, conf):
    if conf['debug']:
        print ("[DEBUG] "+str(text))

def read_configurations():
    try:
        conf = json.loads(open('config/discord_resendmails.json','r').read())
        print ("Configuration loaded! Starting workers!")
        return conf
    except:
        sys.exit(1)

def array_to_queue(arr, q):
    for i in arr:
        q.put(i)
    return q

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
    print("Resending mail for account: " + token + ".")
    headers = get_headers()
    ss = requests.Session()
    if proxy != None:
        proxies = {
            'http' : 'http://' + proxy,
            'https' : 'https://' + proxy
        }
        ss.proxies.update(proxies)
        debug("Testing proxy: " + proxy , conf)
    fingerprint_json = ss.get("https://discordapp.com/api/v6/experiments", timeout=conf['timeout'], headers=headers, verify=False).text
    fingerprint = json.loads(fingerprint_json)["fingerprint"]
    debug("Finger print: " + fingerprint, conf)
    time.sleep(conf['sleepdelay'])
    headers['X-Fingerprint'] = fingerprint
    headers['Authorization'] = token
    headers['X-Super-Properties'] = 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzczLjAuMzY4My4xMDMgU2FmYXJpLzUzNy4zNiIsImJyb3dzZXJfdmVyc2lvbiI6IjczLjAuMzY4My4xMDMiLCJvc192ZXJzaW9uIjoiMTAiLCJyZWZlcnJlciI6IiIsInJlZmVycmluZ19kb21haW4iOiIiLCJyZWZlcnJlcl9jdXJyZW50IjoiIiwicmVmZXJyaW5nX2RvbWFpbl9jdXJyZW50IjoiIiwicmVsZWFzZV9jaGFubmVsIjoic3RhYmxlIiwiY2xpZW50X2J1aWxkX251bWJlciI6MzU1NDAsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9'
    response = ss.post('https://discordapp.com/api/v6/auth/verify/resend', headers=headers, timeout=conf['timeout'], verify=False)
    if response.status_code == 204:
        print("Successfully sent it.")
    else:
        print(response.text)
    return True

def worker(conf):
    while not tokens_q.empty():
        token = tokens_q.get()
        tokens_q.task_done()
        proxy = None
        if conf['use_proxies']:    
            proxy = proxies_q.get()
            proxies_q.put(proxy)
            proxies_q.task_done()
        
        try:
            verify(token, proxy, conf)
        except:
            time.sleep(conf['sleepdelay'])
            pass

def main():
    global tokens_q
    global proxies_q
    conf = read_configurations()
    debug("Starting", conf)
    proxies = [x.rstrip() for x in open(conf['proxy_file'], 'r').readlines()]
    proxies_q = array_to_queue(proxies, proxies_q)
    data = [x.rstrip() for x in open(conf['tokens_file'], 'r').readlines()]
    tokens = []
    for _ in data:
        token = _
        tokens.append(token)
    tokens_q = array_to_queue(tokens, tokens_q)
    tx = []
    debug("Starting "+str(conf['nb_threads'])+" threads", conf)
    for i in range(conf['nb_threads']):
        mT = threading.Thread(target=worker, args=(conf, ))
        mT.start()
        tx.append(mT)
    for t in tx:
        t.join()
    debug("Finished", conf)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    main()