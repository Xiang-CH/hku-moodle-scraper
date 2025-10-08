import dotenv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
from pprint import pprint
import json

dotenv.load_dotenv()

URL = "https://moodle.hku.hk"
USERNAME = os.getenv("EMAIL")
PASSWORD = os.getenv("PORTAL_PIN")
browserStatePath = os.getcwd() + "/state.json"


def wait_and_click(driver, by, selector, timeout=10, attempts=3, pause=0.2):
	"""Wait until locator is clickable then click, retrying on stale element."""
	for attempt in range(attempts):
		try:
			WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, selector)))
			driver.find_element(by, selector).click()
			return
		except StaleElementReferenceException:
			if attempt == attempts - 1:
				raise
			time.sleep(pause)


def wait_and_send_keys(driver, by, selector, value, timeout=10, attempts=3, pause=0.2):
	"""Wait until locator is present then send keys, retrying on stale element."""
	for attempt in range(attempts):
		try:
			WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by, selector)))
			el = driver.find_element(by, selector)
			try:
				el.clear()
			except Exception:
				# some inputs don't support clear(); ignore
				pass
			el.send_keys(value)
			return
		except StaleElementReferenceException:
			if attempt == attempts - 1:
				raise
			time.sleep(pause)


def get_timeline(driver):
	driver.get(URL + "/my/")
	print("On dashboard page")
	WebDriverWait(driver, 5).until(
		EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[data-region="event-list-loading-placeholder"]'))
	)
	pg_data = driver.find_element(By.CSS_SELECTOR, 'div[data-region="event-list-content"]').get_attribute('innerHTML')
	print("Login verification successful")
	return BeautifulSoup(pg_data, 'html.parser')

def moodle_html(headless=False):
	options = Options()
	if headless:
		options.add_argument("--headless")
	options.add_argument("--user-data-dir=browser-data")
	driver = webdriver.Chrome(options=options)
	
	try:
		driver.get(URL + "/login/index.php?authCAS=CAS")

		# Refresh page to load session
		# driver.refresh()
		print("Opened moodle")

		# wait for redirect to Moodle, but avoid infinite loop
		start = time.time()
		LOGIN_TIMEOUT = 60
		while not driver.current_url.startswith(URL):
			if time.time() - start > LOGIN_TIMEOUT:
				raise TimeoutException("Timed out waiting for Moodle redirect during login")
			# Use domain checks and robust re-find/click/send_keys helpers
			cur = driver.current_url
			if "hkuportal.hku.hk" in cur or "cas" in cur:
				# AAD / portal page
				print("On AAD page")
				wait_and_send_keys(driver, By.ID, "email", USERNAME, timeout=10)
				wait_and_click(driver, By.ID, "login_btn", timeout=10)
			elif "adfs.connect.hku.hk" in cur:
				print("On ADFS page")
				wait_and_send_keys(driver, By.ID, "passwordInput", PASSWORD, timeout=10)
				wait_and_click(driver, By.ID, "submitButton", timeout=10)
				time.sleep(1) # wait for possible redirect
			elif "login.microsoftonline.com" in cur:
				print("On Microsoft login page")
				wait_and_click(driver, By.ID, "idSIButton9", timeout=10)
				time.sleep(1) # wait for possible redirect
			else:
				if driver.current_url.startswith(URL):
					break
				# Unknown page, ask user to login manually if interactive
				print(f"Unknown page ({cur}), please login manually if not redirected to Moodle")
				if headless:
					raise Exception("Login expired in headless mode")
				print("Press Enter after you have successfully logged in and can see the dashboard")
				input()
		
		time.sleep(1)  # wait for redirect
		print("Logged in successfully")
		# Check if logged in and get timeline
		timeline = get_timeline(driver)
		if timeline is not None:
			return timeline
		else:
			print("Login verification failed. Please try again.")
			raise Exception("Login failed!")
	except Exception as e:
		print(f"Error during login: {e}")
		if not headless: input("Press Enter to close browser...")
	finally:
		driver.quit()

def get_moodle_deadlines(headless=True):
	soup = moodle_html(headless)
	deadlines = []
	events = soup.find_all(lambda tag: tag.name == 'div' and
							('data-region' in tag.attrs and tag['data-region'] == 'event-list-content-date' or
							'data-region' in tag.attrs and tag['data-region'] == 'event-list-item'))

	time_stamp = 0
	for event in events:
		if event['data-region'] == 'event-list-content-date':
			time_stamp = int(event.attrs['data-timestamp'])
			continue

		due_time = event.select('small')[0].text.strip()


		event_ = event.find('a')
		link = event_.attrs['href']
		id = link.split("?id=")[1]
		title = event_.text.strip()
		course = event.select('small')[1].text.split("·")[1].strip()
		deadlines.append({
			"id": id,
			"time_stamp": time_stamp,
			"link": link,
			"title": title,
			"course": course,
			"due_time": due_time
		})

	return deadlines

if __name__ == "__main__":
	pprint(get_moodle_deadlines(headless=False))
