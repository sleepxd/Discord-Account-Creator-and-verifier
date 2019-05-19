import requests
import time
import json

try:
	from urllib import quote_plus
except ImportError:
	from urllib.parse import quote_plus

conf = json.loads(open(f"config/recaptcha.json",f"r").read())
url = quote_plus(f"https://discordapp.com/register")

def GetCaptcha(ID=None, proxy=None, times=0):
    try:
        captcha_id = None
        s = requests.Session()
        if ID==None:
            captcha_id = s.get(f"http://2captcha.com/in.php?key={conf[f'captchakey']}&method=userrecaptcha&googlekey={conf[f'sitekey']}&pageurl={url}" + ("&proxytype=HTTPS&proxy={proxy}" if proxy != None else ""), timeout=5).text.split('|')[1]
            if(captcha_id == f"ERROR_ZERO_BALANCE"):
                print(f"[CAPTCHA] Your 2captcha account is empty, please refill it.")
                time.sleep(300)
                return GetCaptcha(None, proxy)
            elif captcha_id == f"ERROR_NO_SLOT_AVAILABLE":
                print(f"[CAPTCHA] No slot available. Retrying in 5 minutes.")
                time.sleep(300)
        else:
            captcha_id = ID
        print (f"[CAPTCHA] Contacting 2captcha for completion of captcha, please wait...")
        time.sleep(15)
        while 1:
            if times>=50:
                return GetCaptcha(captcha_id, proxy)
            
            recaptcha_answer = s.get(f"http://2captcha.com/res.php?key={conf[f'captchakey']}&action=get&id={captcha_id}", timeout=15)
            if recaptcha_answer.status_code != 200:
                time.sleep(5)
                times+=1
                continue
            if 'CAPCHA_NOT_READY' not in recaptcha_answer.text:
                break
            time.sleep(5)
            times+=1
        if(recaptcha_answer.text == f"ERROR_CAPTCHA_UNSOLVABLE"):
            return GetCaptcha(None, proxy, 0)
        else:
            if (recaptcha_answer.text == f"ERROR_WRONG_CAPTCHA_ID"):
                return GetCaptcha(None, proxy, 0)
            print (f"[CAPTCHA] Captcha solved.")
            answer = recaptcha_answer.text.split('|')[1]
            return answer + "|" + captcha_id
    except Exception as e:
        print (e)
        time.sleep(5)
        return GetCaptcha(captcha_id, proxy, times)

def reportCaptcha(ID, state, times=0):
    s = requests.Session()
    recaptcha_answer = s.get(f"http://2captcha.com/res.php?key={conf[f'captchakey']}&action=report{state}&id={ID}", timeout=15)
    if recaptcha_answer.status_code != 200:
        if times>=5:
            print(f"[CAPTCHA] Failed to report {state} captcha result after 5 tries, API down? (ID: {ID})")
        else:
            time.sleep(5)
            times+=1
            reportCaptcha(ID, state, times)
    else:
        print(f"[CAPTCHA] Reported {state} captcha" + (", refunds will be made once it has been reviewed." if state == "bad" else ", no refund is expected as it was successful."))