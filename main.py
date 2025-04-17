from playwright.sync_api import sync_playwright
import time  # For execution time calculation
import random
import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TWITTER_USERNAME = os.getenv("TWITTER_USERNAME")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD")

# Session storage file path
STORAGE_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "twitter_session.json")

retweeted_links_count = 0

def random_delay(min_seconds=1, max_seconds=3):
    """Add random delay to mimic human behavior"""
    time.sleep(random.uniform(min_seconds, max_seconds))

def is_logged_in(page):
    """Check if the user is already logged in"""
    try:
        # Check for elements that are typically present on a logged-in home timeline
        return page.is_visible('div[aria-label="Home timeline"], a[aria-label="Home"], a[data-testid="AppTabBar_Home_Link"]', 
                              timeout=5000)
    except:
        return False

def login_to_twitter(page):
    """Handles the Twitter login process"""
    print("Logging in to Twitter...")
    
    # Go to Twitter login page
    page.goto('https://twitter.com/i/flow/login')
    random_delay(2, 4)
    
    # Wait for username field and fill it
    username_selector = 'input[autocomplete="username"], input[name="text"]'
    page.wait_for_selector(username_selector, timeout=10000)
    page.fill(username_selector, TWITTER_USERNAME)
    random_delay()
    
    # Click the Next button 
    next_button = page.locator("text='Next'")
    if (next_button.is_visible()):
        next_button.click()
    else:
        # Alternative selector
        page.click('div[role="button"][data-testid="LoginForm_Login_Button"], div[data-testid="auth_input_submit_button"]')
    random_delay(2, 3)
    
    # Check if verification is requested
    verify_selector = 'input[data-testid="ocfEnterTextTextInput"]'
    if page.is_visible(verify_selector, timeout=3000):
        print("Twitter is asking for verification. Manual intervention needed.")
        # Wait for manual verification 
        page.wait_for_selector('input[name="password"]', timeout=60000)
    
    # Wait for and fill password
    page.wait_for_selector('input[name="password"]', timeout=10000)
    page.fill('input[name="password"]', TWITTER_PASSWORD)
    random_delay()
    
    # Click the Log in button
    login_button = page.get_by_role("button", name="Log in")
    if login_button.is_visible():
        login_button.click()
    else:
        # Alternative selector
        page.click('div[data-testid="LoginForm_Login_Button"]')
    
    # Wait for home page to load 
    page.wait_for_selector('div[aria-label="Home timeline"], a[aria-label="Home"], a[data-testid="AppTabBar_Home_Link"]', timeout=20000)
    print("Successfully logged in")
    random_delay(3, 5)

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
    tweet_links_set = set()  
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
    
    return list(tweet_links_set)  

def process_unread_dms(context, page):
    """Process unread DMs and scroll through the DM list."""
    processed_dms = 0  # Track the number of processed DMs

    for i in range(20):  # Adjust this number to control how many times to scroll
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
       
def unread_count():
    """Get the unread DM count and return it"""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser_context_options = {
            "viewport": {"width": 1280, "height": 800}
        }
        
        if os.path.exists(STORAGE_STATE_PATH):
            browser_context_options["storage_state"] = STORAGE_STATE_PATH
        
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(**browser_context_options)
        page = context.new_page()
        
        page.goto('https://twitter.com/home')
        random_delay(2, 4)
        
        if not is_logged_in(page):
            print("Not logged in. Logging in...")
            login_to_twitter(page)
            context.storage_state(path=STORAGE_STATE_PATH)
        else:
            print("Using existing session - already logged in")
        
        print("Navigating to Direct Messages...")
        page.goto('https://twitter.com/messages')
        page.wait_for_timeout(7000)
        
        process_unread_dms(context, page)
        browser.close()

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

if __name__ == "__main__":
    start_time = time.time()  # Record the start time

    print("=== Twitter Unread DM Retweeter ===")
    print("This script will open unread DM conversations and retweet any links found")
    
    if not TWITTER_USERNAME or not TWITTER_PASSWORD:
        print("Error: Please set TWITTER_USERNAME and TWITTER_PASSWORD environment variables in your .env file")
        exit(1)
    
    print("\nOptions:")
    print("1: Retweet from unread DMs")
    print("2: Delete saved session")
    print("3: Exit")
    
    choice = input("\nEnter your choice (1-3): ")
    
    if choice == "1":
        unread_count()
    elif choice == "2":
        if os.path.exists(STORAGE_STATE_PATH):
            os.remove(STORAGE_STATE_PATH)
            print(f"Session file {STORAGE_STATE_PATH} deleted")
        else:
            print("No session file found to delete")
    else:
        print("Invalid option selected")

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"\n=== Summary ===")
    print(f"Total Execution Time: {execution_time:.2f} seconds")
    print(f"Total Links Retweeted: {retweeted_links_count}")
