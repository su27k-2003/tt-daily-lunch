import requests, os, time, json
from datetime import date,timedelta
import numpy as np
from github import Github
from github import Auth
from bs4 import BeautifulSoup


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


def todays_meal_url(today, retry, user_jwt):
    
    meal_url_base = "https://hampr.com.au/program-meal/"
    # workspace/1565 = TikTok - Darling Park
    programmeal_url = "https://api.hampr.com.au/api/v1/workspace/1565/schedule-between?startDate="+str(today)+"&endDate="+str(today)
    #programmeal_url = "https://api.hampr.com.au/api/v1/workspace/1565/schedule-between?startDate=2024-06-11&endDate=2024-06-11"
    #print(programmeal_url)

    header = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie": user_jwt
    }

    for i in range(retry):
        try:
            res = requests.get(url = programmeal_url, headers = header)

            if res.status_code not in [200, 404]:
                time.sleep(5) #tries to retrieve the URL, if 200 or 404 is not received, waits 5 seconds before trying again
            else:
                data = json.loads(res.text) # Load json data in {}

                # Sometimes (unbooked day?) programMealId in data[1] rather than data[0]
                try:
                    if data[0].get("programMealId"):
                        programmeal_id = data[0].get("programMealId")
                    else:
                        programmeal_id = data[1].get("programMealId")
                except:
                    # If "programMealId" cannot be found then it's Public Holiday/Weekend
                    todays_meal_url = "Could not find programMealId!"
                    #print(todays_meal_url)
                    return todays_meal_url

                todays_meal_url = meal_url_base + str(programmeal_id)
                #print(todays_meal_url)
                return todays_meal_url
        except requests.exceptions.ConnectionError:
            time.sleep(5)
            print("HTTP request failed with meal_url()")
            return "HTTP request failed with meal_url()"


def check_lunch(url, retry, user_jwt):
    # It's Public Holiday today/Weekend
    if url == "Could not find programMealId!":
        date = "Could not find programMealId!"
        lunch = "N/A"
        #print (date, lunch)
        return date, lunch
        
    header = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Cookie": user_jwt
    }

    for i in range(retry):
        try:
            res = requests.get(url = url, headers = header)

            if res.status_code not in [200, 404]:
                time.sleep(5) #tries to retrieve the URL, if 200 or 404 is not received, waits 5 seconds before trying again
            else:
                # parser json data from HTML
                soup = BeautifulSoup(res.text, 'html.parser').find(id="__NEXT_DATA__")
                data = json.loads(soup.text) # Load json data in {}

                try:
                    date = data.get("props").get("pageProps").get("programMeal").get("eventDate") # Check date
                except:
                    # If date cannot be found then it's Public Holiday/Weekend
                    date = "Public Holiday/Weekend"
                    lunch = "N/A"
                    print (date, lunch)
                    return date, lunch
                
                
                try:
                    # Check ordered lunch and vender name
                    lunch = data.get("props").get("pageProps").get("programMeal").get("ProgramMealSelections")[0].get("selection").get("item").get("name")
                    vender_partnerId = data.get("props").get("pageProps").get("programMeal").get("ProgramMealSelections")[0].get("selection").get("item").get("partnerId")
                    #print("vender_partnerId: ", vender_partnerId)
                    
                    # Check vender name
                    try:
                        for i in range(10):
                            vender_id = data.get("props").get("pageProps").get("programMeal").get("Purchases")[0].get("purchaseContentDetails").get("partners")[i].get("partner").get("id")
                            #print("vender_id: ", vender_id)
                            if vender_id == vender_partnerId:
                                vender_name = data.get("props").get("pageProps").get("programMeal").get("Purchases")[0].get("purchaseContentDetails").get("partners")[i].get("partner").get("name")
                                #print("vender: ", vender_name)
                                break
                    except:
                        vender_name = "Not Found"
                        #print("vender_name: ", vender_name)

                except:
                    # If date can be found, but lunch cannot be found then lunch unbooked
                    lunch = "Unbooked"
                    vender_name = "N/A"
                    print (date, lunch, vender_name)
                    return date, lunch, vender_name
                
                print (date, lunch, vender_name)
                return date, lunch, vender_name
        except requests.exceptions.ConnectionError:
            time.sleep(5)
            print("HTTP request failed with check_lunch()")
            return "HTTP request failed with check_lunch()"


def git_commit(data):
    repo = g.get_repo("su27k-2003/tt-daily-lunch")
    contents = repo.get_contents("index.html")
    
    # Commit to index.html in main branch withtou ', (, )
    repo.update_file(contents.path, "lunch", str(data).replace("'", "").replace("(", "").replace(")", ""), contents.sha, branch="main")
    print("Git commit done!")
    g.close()



if __name__ == '__main__':
    login_url = "https://api.hampr.com.au/api/v1/account/login"
    retry = 5

    # Update index.html file in the Github repo
    # using an access token
    auth = Auth.Token(os.environ['git_token'])
    # Public Web Github
    g = Github(auth=auth)

    # Get user token
    user_jwt = get_userjwt(login_url, retry)

    # Check today's lunch
    #today = date.today() 
    today = date.today() + timedelta(days=1) # since cronjob in Github was setup at 22:00 UTC which is a day before AU UTC+10
    check_lunch(url=todays_meal_url(today, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt)

    #git_commit(data = check_lunch(url=todays_meal_url(today, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt))

    #Check lunchs for the next week
    next_week = date.today() + timedelta(days=3)
    print(next_week)
    #check_lunch(url=todays_meal_url(next_week, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt)

    if "Unbooked" in check_lunch(url=todays_meal_url(next_week, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt):
        attention = "ATTENTION: Book lunch for " + str(next_week) + "!!!\n"
        print(attention)
        #print("git_commit...")
        git_commit(data = attention + str(check_lunch(url=todays_meal_url(today, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt)))
    elif "Could not find programMealId!" in check_lunch(url=todays_meal_url(next_week, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt):
        attention = "ATTENTION: Could not find programMealId for " + str(next_week) + "!!!\n"
        print(attention)
        #print("git_commit...")
        git_commit(data = attention + str(check_lunch(url=todays_meal_url(today, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt)))
    else:
        print("lunch booked for the next week")
        git_commit(data = check_lunch(url=todays_meal_url(today, retry=retry, user_jwt=user_jwt), retry=retry, user_jwt=user_jwt))