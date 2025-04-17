import hashlib
from playwright.sync_api import sync_playwright
import time
import random
import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")

USERNAME = os.getenv("MULTILOGIN_USERNAME")
PASSWORD = os.getenv("MULTILOGIN_PASSWORD")

FOLDER_ID = os.getenv("FOLDER_ID")
PROFILE_IDS = os.getenv("PROFILE_IDS").split(",")  # Load PROFILE_IDS from .env and split into a list

MLX_BASE = "https://api.multilogin.com"
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}
retweeted_links_count = 0

def random_delay(min_seconds=1, max_seconds=3):
    time.sleep(random.uniform(min_seconds, max_seconds))

def is_logged_in(page):
    try:
        return page.is_visible('div[aria-label="Home timeline"], a[aria-label="Home"], a[data-testid="AppTabBar_Home_Link"]', timeout=5000)
    except:
        return False

def send_message_in_dm(page, message):
    """Send a message in the current DM conversation"""
    try:
        message_input = page.locator('.DraftEditor-root div[contenteditable="true"]')
        message_input.wait_for(timeout=5000)
        message_input.fill(message)
        random_delay(1, 2)
        message_input.press("Enter")
    except Exception as e:
        print(f"Error sending message: {str(e)}")

def retweet_tweets(context, tweet_links_list):
    """Retweet all tweets in the provided list of tweet links"""
    global retweeted_links_count 
    for tweet_link in tweet_links_list:
        tweet_page = context.new_page()
        tweet_page.goto(tweet_link)
        
        random_delay(3, 5)
        print("Successfully opened tweet page")

        print("Looking for retweet button...")

        retweet_js = """
            () => {
                // Check if the tweet is already retweeted
                const unretweetBtn = document.querySelector('[data-testid="unretweet"]');
                if (unretweetBtn) {
                    console.log("Tweet is already retweeted. Undoing retweet...");
                    unretweetBtn.click();
                    return "undo";
                }

                // Look for the normal retweet button
                const retweetBtn = document.querySelector('[data-testid="retweet"]');
                if (retweetBtn) {
                    console.log("Retweeting the tweet...");
                    retweetBtn.click();
                    return "retweet";
                }
                return false;
            }
        """
        action = tweet_page.evaluate(retweet_js)

        if action == "undo":
            random_delay(2, 4)

            confirm_undo_js = """
                () => {
                    const undoBtn = document.querySelector('[data-testid="unretweetConfirm"]');
                    if (undoBtn) {
                        console.log("Confirming undo retweet...");
                        undoBtn.click();
                        return true;
                    }
                    return false;
                }
            """
            undo_success = tweet_page.evaluate(confirm_undo_js)
            if undo_success:
                print("Undo successful. Retweeting again...")
                random_delay(3, 5)

                # Ensure we retweet again after undoing
                action = tweet_page.evaluate(retweet_js)

        if action == "retweet":
            random_delay(1, 2)

            confirm_js = """
                () => {
                    const confirmBtn = document.querySelector('[data-testid="retweetConfirm"]');
                    if (confirmBtn) {
                        console.log("Confirming retweet...");
                        confirmBtn.click();
                        return true;
                    }
                    return false;
                }
            """
            confirm_success = tweet_page.evaluate(confirm_js)
            if confirm_success:
                print("Successfully retweeted!")
                retweeted_links_count += 1  
                random_delay(2, 3)

        tweet_page.close()

def get_tweet_links(messages, message_count, unread_msg_count):
    tweet_links_set = set()  # Use a set to avoid duplicates
    for j in range(message_count - 1, message_count - unread_msg_count - 1, -1):
        message_content = messages.nth(j).inner_text()
        tweet_links = messages.nth(j).locator('a[href*="/status/"]')
        tweet_link_count = tweet_links.count()
        
        for k in range(tweet_link_count):
            tweet_link = tweet_links.nth(k).get_attribute('href')
            if tweet_link:  # Ensure the link is not None
                tweet_links_set.add(f'https:/x.com{tweet_link}')
        
        if "https://twitter.com/" in message_content:
            tweet_links_set.add(message_content)
    
    return list(tweet_links_set)  # Convert the set back to a list

def process_unread_dms(context, page):
    """Process unread DMs and scroll through the DM list."""
    processed_dms = 0 

    for i in range(20): 
        # Check for unread DMs
        unread_dms = page.locator(".r-615f2u")
        unread_count = unread_dms.count()

        print(f"Unread DMs found: {unread_count}")
        if unread_count > 0:
            for j in range(unread_count):
                unread_dms = page.locator(".r-615f2u")
                if unread_dms.count() > 0:
                    unread_dms.first.click()
                    print(f"Opened unread DM {processed_dms + 1}")
                    random_delay(2, 4)

                    unread_divider = page.locator('.css-175oi2r .r-5oul0u')
                    random_delay(2, 4)
                    if unread_divider.count() > 0:
                        unread_msg_count = int((unread_divider.nth(0).inner_text())[0])
                        print(f"Number of unread messages: {unread_msg_count}")

                        messages = page.locator('div[data-testid="messageEntry"]')
                        message_count = messages.count()
                        print(f"Total messages found: {message_count}")

                        tweet_links_list = get_tweet_links(messages, message_count, unread_msg_count)
                        print("Tweet links: " + str(tweet_links_list))
                        
                        if tweet_links_list:
                            send_message_in_dm(page, '''Done ✅ RTxRT or Refresh 🔄 !! NO FAKE❌
(I always check)❗️

My link: 👉🏻https://x.com/ts_Bellaa/status/1907965866953654535/video/1👈

✨Send me your link✨
Managed by 
@OrcaSocials_

International Marketing Company
More than 4 Millions users on our network''')
                            retweet_tweets(context, tweet_links_list)
                        
                    else:
                        print("No unread messages found.")

                    processed_dms += 1
                else:
                    print("No more unread DMs found.")
                    break
        else:
            print("No unread DMs found on this screen.")

        # Scroll within the side screen to load more DMs
        print(f"Scrolling DM list... ({i + 1}/20)")
        scroll_js = """
            () => {
                const messagesDiv = document.querySelector('div.css-175oi2r.r-150rngu.r-16y2uox.r-1wbh5a2.r-33ulu8');
                if (messagesDiv) {
                    messagesDiv.scrollTop = messagesDiv.scrollHeight;
                }
            }
        """
        page.evaluate(scroll_js)
        random_delay(5, 7)  # Delay to allow content to load

    print("Finished scrolling through the DM list.")
 
def sign_in():
    payload = {
        "email": USERNAME,
        "password": hashlib.md5(PASSWORD.encode()).hexdigest(),
    }
    r = requests.post(f"{MLX_BASE}/user/signin", json=payload)
    if r.status_code == 200:
        return r.json()["data"]["token"]
    else:
        raise Exception(f"Login failed: {r.text}")

def handle_profile(profile_id):
    token = sign_in()
    HEADERS["Authorization"] = os.getenv("MULTILOGIN_AUTHORIZATION")
    with sync_playwright() as pw:
        response = requests.get(
            f"https://launcher.mlx.yt:45001/api/v2/profile/f/{FOLDER_ID}/p/{profile_id}/start?automation_type=playwright&headless_mode=false",
            headers=HEADERS
        )
        if response.status_code != 200:
            print(f"Failed to start profile: {response.text}")
            return

        browser_port = response.json()["data"]["port"]
        browser_url = f"http://127.0.0.1:{browser_port}"

        browser = pw.chromium.connect_over_cdp(endpoint_url=browser_url)
        context = browser.contexts[0]
        page = context.new_page()

        print("Navigating to Direct Messages...")
        page.goto('https://twitter.com/messages')
        page.wait_for_timeout(5000)
        process_unread_dms(context, page)

        context.close()
        browser.close()
        requests.get(f"https://launcher.mlx.yt:45001/api/v2/profile/stop/{profile_id}", headers=HEADERS)

if __name__ == "__main__":
    start_time = time.time()
    print("\n=== Twitter Multi-Profile DM Retweeter ===")
    print("Launching profiles...")

    with ThreadPoolExecutor(max_workers=len(PROFILE_IDS)) as executor:
        executor.map(handle_profile, PROFILE_IDS)

    end_time = time.time()
    execution_time = end_time - start_time
    print("\n=== Summary ===")
    print(f"Total Execution Time: {execution_time:.2f} seconds")
    print(f"Total Links Retweeted: {retweeted_links_count}")