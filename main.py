import datetime
import time

import requests
import json

from requests_oauthlib import OAuth2Session
from csv import reader
from PIL import Image
import re


def deEmojify(text):
    regrex_pattern = re.compile(pattern="["
                                        u"\U0001F600-\U0001F64F"  # emoticons
                                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                                        "]+", flags=re.UNICODE)
    return regrex_pattern.sub(r'', text)


def download_file(url):
    local_filename = url.split('/')[-1]
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                # if chunk:
                f.write(chunk)
    return local_filename


def upload_ad(row):  # create creative and upload ad from csv row
    creative_name = row[0]
    headline = row[1]
    url = row[2]
    picture_url = row[3]
    max_bid = float(row[4].replace(",", "."))
    budget = float(row[5].replace(",", "."))

    data = {"campaigns": [
        {"name": headline, "ad_account_id": account_id, "status": "ACTIVE",
         "start_time": f"{date.year}-{date.month}-{date.day}T{date.hour}:{date.minute}:{date.second}.{date.microsecond}Z"}]}
    hed = {'Authorization': 'Bearer ' + snap_credentials['access_token']}
    req = requests.post(
        f"https://adsapi.snapchat.com/v1/adaccounts/{account_id}/campaigns", json=data, headers=hed)
    camp_id = req.json()["campaigns"][0]["campaign"]["id"]
    data = {"adsquads": [
        {"id": "7e52b0f4-a3fc-46f2-9a33-f03d71c55047", "name": headline, "status": "ACTIVE",
         "campaign_id": camp_id, "type": "SNAP_ADS",
         "targeting": {"regulated_content": False,
                       "geos": [{"country_code": "de"}, {"country_code": "at"}, {"country_code": "ch"}],
                       # "devices": [{"os_type": "iOS"},{"os_type": "ANDROID"}],
                       "enable_targeting_expansion": False}, "placement_v2": {"config": "AUTOMATIC"},
         "billing_event": "IMPRESSION", "bid_strategy": "LOWEST_COST_WITH_MAX_BID",
         "bid_micro": int(max_bid * 1000000),
         "daily_budget_micro": int(budget * 1000000),
         "start_time": f"{date.year}-{date.month}-{date.day}T{date.hour}:{date.minute}:{date.second}.{date.microsecond}Z",
         "optimization_goal": "SWIPES", }]}

    req = requests.post(
        f"https://adsapi.snapchat.com/v1/campaigns/{camp_id}/adsquads", json=data, headers=hed)
    ad_squad_id = req.json()["adsquads"][0]["adsquad"]["id"]
    # create meadia
    data = {"media": [{"name": headline + " Image", "type": "IMAGE", "ad_account_id": f"{account_id}"}]}
    req = requests.post(f"https://adsapi.snapchat.com/v1/adaccounts/{account_id}/media", json=data,
                        headers=hed)
    media_id = req.json()["media"][0]["media"]["id"]
    # upload image to media
    filename = download_file(picture_url)
    img = Image.open(filename)
    # img = img.resize((1080, 1920), Image.ANTIALIAS)  # Resize image to match snapchat image format
    new_size = (1080, 1920)
    wpercent = (1080 / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((1080, hsize), Image.ANTIALIAS)

    old_im = img
    old_size = old_im.size

    new_im = Image.new("RGB", new_size)  ## luckily, this is already black!
    new_im.paste(old_im, ((new_size[0] - old_size[0]) // 2,
                          (new_size[1] - old_size[1]) // 2))
    new_im.save('upload.png')
    files = {'file': (open("upload.png", 'rb'))}

    req = requests.post(f"https://adsapi.snapchat.com/v1/media/{media_id}/upload", files=files,
                        headers=hed)

    # create creative
    if not req.ok:
        print(req.json())
        print(f"Error with {headline}")
        return False
    data = {"creatives": [{"ad_account_id": account_id, "brand_name": "Viralpost",
                           "top_snap_media_id": media_id, "name": creative_name,
                           "type": "WEB_VIEW", "headline": deEmojify(headline[:34]),
                           "shareable": True, "call_to_action": "VIEW",
                           "web_view_properties": {"url": url}}]}

    req = requests.post(f"https://adsapi.snapchat.com/v1/adaccounts/{account_id}/creatives",
                        headers=hed, json=data)
    creative_id = req.json()["creatives"][0]["creative"]["id"]
    # create ad
    data = {"ads": [
        {"ad_squad_id": ad_squad_id, "creative_id": creative_id,
         "name": headline, "type": "REMOTE_WEBPAGE", "status": "ACTIVE"}]}
    req = requests.post(f"https://adsapi.snapchat.com/v1/adsquads/{ad_squad_id}/ads", json=data, headers=hed)
    print(f"Created {headline}")
    time.sleep(3)


scope = ['snapchat-marketing-api']
account_id = "924959e3-8080-4aaf-b48e-03dc63c5eec1"
authorize_url = 'https://accounts.snapchat.com/login/oauth2/authorize'
access_token_url = 'https://accounts.snapchat.com/login/oauth2/access_token'
protected_url = 'https://adsapi.snapchat.com/v1/me/organizations'

with open('credentials.json', 'r') as f:
    snap_credentials = json.load(f)
oauth = OAuth2Session(
    snap_credentials['client_id'],
    redirect_uri=snap_credentials['redirect_url'],
    scope=scope
)

authorization_url, state = oauth.authorization_url(authorize_url)
print('Please go to %s and authorize access.' % authorization_url)

authorization_response = input('Enter the full callback URL: ')

token = oauth.fetch_token(
    access_token_url,
    authorization_response=authorization_response,
    client_secret=snap_credentials['client_secret'],
    scope=scope
)

snap_credentials['access_token'] = oauth.token['access_token']
snap_credentials['refresh_token'] = oauth.token['refresh_token']  #

access_params = {
    'client_id': snap_credentials['client_id'],
    'client_secret': snap_credentials['client_secret'],
    'code': snap_credentials['refresh_token'],  # Get it in first step in redirect URL
    'grant_type': 'refresh_token',
}

res = requests.post(
    access_token_url,
    params=access_params
)

snap_credentials['access_token'] = res.json()['access_token']
snap_credentials['refresh_token'] = res.json()['refresh_token']

with open('credentials.json', 'w') as f:
    json.dump(snap_credentials, f)  # save refresh and access token

date = datetime.datetime.now()

with open("snapchat_ads.csv", "r", encoding="utf-8") as f:
    csv_file = reader(f, delimiter=",")
    rows = [i for i in csv_file]

for row in rows[1:]:
    try:
        upload_ad(row)  # create ad
    except Exception as e:

        # if token expired create new token and try again

        data = {"refresh_token": snap_credentials["refresh_token"], "client_id": snap_credentials["client_id"],
                "grant_type": "refresh_token", "client_secret": snap_credentials["client_secret"]}
        req = requests.post("https://accounts.snapchat.com/login/oauth2/access_token", data=data)
        snap_credentials["access_token"] = req.json()["access_token"]

        upload_ad(row)
