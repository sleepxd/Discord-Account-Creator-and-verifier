import sys
import re
import requests
import json
import queue
import threading
import time
from requests.packages.urllib3.exceptions import InsecureRequestWarning

proxies_q = queue.Queue()

def read_configurations():
    try:
        conf = json.loads(open('config/proxychecker.json','r').read())
        print ("Configuration loaded! Starting workers!")
        return conf
    except:
        sys.exit(1)

def array_to_queue(arr, q):
    for i in arr:
        q.put(i)
    return q

def save_proxy(proxy, conf):
    print("Found good proxy, saving proxy!")
    output = open(conf['output_file'], 'a')
    output.write(":".join(
        [proxy]
        )+"\n")
    output.close()

def get_headers():
    return {
        'user-agent': 'Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16',
        'Host': 'discordapp.com',
        'Accept': '*/*',
        'Accept-Language': 'en-US',
        'Content-Type': 'application/json',
        'Referer': 'https://discordapp.com/register',
        'DNT': '1',
        'Connection': 'keep-alive'
    }

def verify(conf):
    try:
        headers = get_headers()
        ss = requests.Session()
        proxy = proxies_q.get()
        proxies_q.task_done()
        if proxy != 'none':
            proxies = {
                'http' : 'http://' + proxy,
                'https' : 'https://' + proxy
            }
            ss.proxies.update(proxies)
    
        response  = ss.post('https://discordapp.com/api/v6/experiments', proxies=proxies, timeout=conf['timeout'])
        save_proxy(proxy, conf)
    except:
        print("Found faulty proxy.")
        return False
    return True

def worker(conf):
    while not proxies_q.empty():
        verify(conf)

def main():
    global proxies_q
    conf = read_configurations()
    print("Starting")
    data = [x.rstrip() for x in open(conf['input_file'], 'r').readlines()]
    proxies = []
    notDone = False
    alreadydone = [x.rstrip() for x in open(conf['output_file'], 'r').readlines()]
    for _ in data:
        try:
            if _ not in alreadydone:
                proxies.append(_)
        except:
            pass
    proxies_q = array_to_queue(proxies, proxies_q)
    
    tx = []
    for i in range(conf['nb_threads']):
        mT = threading.Thread(target=worker, args=(conf, ))
        mT.start()
        tx.append(mT)
    for t in tx:
        t.join()
    
    print("Finished")

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    main()