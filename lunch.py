import requests, os, time, json
from datetime import date,timedelta
import numpy as np
from github import Github
from github import Auth


def get_userjwt(login_url, retry):

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    payload = {
        "email": os.environ['hampr_email'], 
        "password": os.environ['hampr_password']
        }

    for i in range(retry):
        try:
            r = requests.post(url = login_url, headers = headers, json = payload)
            
            if r.status_code not in [200, 404]:
                time.sleep(5) #tries to retrieve the URL, if 200 or 404 is not received, waits 5 seconds before trying again
            else:
                user_jwt = r.headers["Set-Cookie"]
                #print(r.headers["Set-Cookie"])
                return user_jwt #stops function if 200 or 404 received
        except requests.exceptions.ConnectionError:
            pass


def meal_url(today):
    # Check how many week days between '2024-04-15' and today to calculate meal_id
    # e.g. For 2024-04-15, meal_url: https://hampr.com.au/_next/data/duyRCMIOvouBrAGRkN8NC/en-AU/program-meal/8207.json

    meal_url_base = "https://hampr.com.au/_next/data/duyRCMIOvouBrAGRkN8NC/en-AU/program-meal/"
    start_day = '2024-04-29'
    start_day_id = 8591 # 2024-04-29
    # Calculate how many weekdays between the two dates
    day_diff = np.busday_count(start_day, today)
    today_meal_id = start_day_id + day_diff

    meal_url = meal_url_base + str(today_meal_id) + ".json"
    #print(meal_url)
    return meal_url


def check_lunch(meal_url, retry, user_jwt):

    header = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie": user_jwt
    }

    for i in range(retry):
        try:
            res = requests.get(url = meal_url, headers = header)

            if res.status_code not in [200, 404]:
                time.sleep(5) #tries to retrieve the URL, if 200 or 404 is not received, waits 5 seconds before trying again
            else:
                data = json.loads(res.text) # Load HTTP GET response in {}
                
                try:
                    date = data.get("pageProps").get("programMeal").get("eventDate") # Check date
                except:
                    # If date cannot be found then it's Public Holiday
                    date = "Public Holiday"
                    lunch = "No Lunch"
                    print (date, lunch)
                    return date, lunch
                
                try:
                    # Check ordered lunch
                    lunch = data.get("pageProps").get("programMeal").get("ProgramMealSelections")[0].get("selection").get("item").get("name")
                except:
                    # If date can be found but lunch cannot be found then lunch unbooked yet
                    lunch = "Unbooked"
                    print (date, lunch)
                    return date, lunch
                
                print (date, lunch)
                return date, lunch
        except requests.exceptions.ConnectionError:
            time.sleep(5)
            print("HTTP request failed with check_lunch()")
            return "HTTP request failed with check_lunch()"


def git_commit(data):
    repo = g.get_repo("su27k-2003/tt-daily-lunch")
    contents = repo.get_contents("index.html")
    
    # Commit to index.html in main branch withtou ', (, )
    repo.update_file(contents.path, "lunch", str(data).replace("'", "").replace("(", "").replace(")", ""), contents.sha, branch="main")
    g.close()



if __name__ == '__main__':
    login_url = "https://api.hampr.com.au/api/v1/account/login"
    retry = 5
    today = date.today()

    # using an access token
    auth = Auth.Token(os.environ['git_token'])
    # Public Web Github
    g = Github(auth=auth)

    # Check today's lunch
    #check_lunch(meal_url=meal_url(today), retry=retry, user_jwt=get_userjwt(login_url, retry))

    # Update index.html file in the Github repo
    git_commit(data = check_lunch(meal_url=meal_url(today), retry=retry, user_jwt=get_userjwt(login_url, retry)))

    # Check lunchs for the next 5 days
    # for i in range(5):
    #     check_lunch(meal_url=meal_url(today + timedelta(days=i)), retry=retry, user_jwt=get_userjwt(login_url, retry))
    #     time.sleep(1)