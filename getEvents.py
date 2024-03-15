import dotenv
import os
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from pprint import pprint

dotenv.load_dotenv()

URL = "https://moodle.hku.hk/"
USERNAME = os.getenv("EMAIL")
PASSWORD = os.getenv("PORTAL_PIN")
browserStatePath = storage_state=os.getcwd() + "/state.json"
# print(browserStatePath)

def check_if_logged_in(page, context):
    pg_data = page.inner_html("html")
    soup = BeautifulSoup(pg_data, 'html.parser')
    if soup.find(id="loggedin-user") != None:
        print("Already logged in")
        page.wait_for_selector('h2:has-text("My courses")')
        page.goto(URL + "my/")
        # page.click('span:has-text("Dashboard")')
        print("On dashboard page")
        page.wait_for_selector('div[data-region="event-list-loading-placeholder"]', state="hidden")
        pg_data = page.inner_html('div[data-region="event-list-content"]')
        context.storage_state(path=browserStatePath)
        return BeautifulSoup(pg_data, 'html.parser')
    return None

def moodle_html(headless = True):
    with sync_playwright() as p:
        # launch browser context
        browser = p.chromium.launch(headless=headless)
        try:
            context = browser.new_context(storage_state=browserStatePath)
        except FileNotFoundError as e:
            print(e)
            context = browser.new_context()
        # Open new page and go to moodle
        page = context.new_page()
        page.goto(URL)
        print("Opened moodle")

        # Check if user is already logged in
        timeline = check_if_logged_in(page, context)
        if timeline != None:
            return timeline

        
        # If not logged in, login
        page.click('a:has-text("login")')

        # Check if jumped to moodle
        timeline = check_if_logged_in(page, context)
        if timeline != None:
            return timeline

        print("logging in")

        page.wait_for_selector('a:has-text("HKU Portal user login"), h1.portal-title')
        if ("moodle.hku.hk" in page.url):
            page.click('a:has-text("HKU Portal user login")')
        page.fill('input[name="email"]', USERNAME)
        page.click('input:has-text("LOG IN")')

        # Check if user is already logged in
        timeline = check_if_logged_in(page, context)
        if timeline != None:
            return timeline
        
        # If not, input password for microsoft login
        print("On microsoft login page")
        page.fill('input#passwordInput', PASSWORD)
        page.click('span#submitButton')

        # Display 2fa code
        print("Waiting for 2fa code")
        auth_code = page.inner_html('div#idRichContext_DisplaySign')
        print(f"auth_code: {auth_code}")
        print(page.url)
        if "microsoftonline" in page.url:
            page.click('input#idSIButton9')

        # Moodle loaded
        return check_if_logged_in(page, context)

def get_moodle_dealines(headless = True):
    soup = moodle_html(headless)
    dealines = []
    events = soup.find_all(lambda tag: tag.name == 'div' and
                            ('data-region' in tag.attrs and tag['data-region'] == 'event-list-content-date' or
                            'data-region' in tag.attrs and tag['data-region'] == 'event-list-item'))

    time_stamp = 0
    for event in events:
        if event['data-region'] == 'event-list-content-date':
            time_stamp = int(event.attrs['data-timestamp'])
            continue

        due_time = event.select('small.text-right.text-nowrap.pull-right')[0].text.strip()
        # time_diff = event.select('small.text-right.text-nowrap.pull-right')[0].text.split(":")
        # time_stamp += int(time_diff[0]) * 3600 + int(time_diff[1]) * 60

        event_ = event.find('a')
        link = event_.attrs['href']
        id = link.split("?id=")[1]
        title = event_.attrs['title']
        course = event_.find('small').text
        dealines.append({
            "id": id,
            "time_stamp": time_stamp,
            "link": link,
            "title": title,
            "course": course,
            "due_time": due_time
        })

    return dealines

        

if __name__ == "__main__":
    pprint(get_moodle_dealines(headless=False))