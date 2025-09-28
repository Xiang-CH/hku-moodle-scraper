import dotenv
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pprint import pprint
import json

dotenv.load_dotenv()

URL = "https://moodle.hku.hk/"
USERNAME = os.getenv("EMAIL")
PASSWORD = os.getenv("PORTAL_PIN")
browserStatePath = os.getcwd() + "/state.json"

def save_session_state(driver, path):
	state = {
		'cookies': driver.get_cookies(),
	}
	with open(path, 'w') as file:
		json.dump(state, file)

def load_session_state(driver, path):
	try:
		with open(path, 'r') as file:
			state = json.load(file)

		# Clear existing cookies and storage
		driver.delete_all_cookies()
			
		# Load cookies
		for cookie in state.get('cookies', []):
			driver.add_cookie(cookie)
			
		return True
	except (FileNotFoundError, Exception) as e:
		# print(e)
		return False

def check_if_logged_in(driver):
	try:
		WebDriverWait(driver, 5).until(
			EC.presence_of_element_located((By.XPATH, '//h2[contains(text(), "My courses")]'))
		)
		driver.get(URL + "my/")
		print("On dashboard page")
		WebDriverWait(driver, 5).until(
			EC.invisibility_of_element_located((By.CSS_SELECTOR, 'div[data-region="event-list-loading-placeholder"]'))
		)
		pg_data = driver.find_element(By.CSS_SELECTOR, 'div[data-region="event-list-content"]').get_attribute('innerHTML')
		print("Login verification successful")
		save_session_state(driver, browserStatePath)
		return BeautifulSoup(pg_data, 'html.parser')
	except (NoSuchElementException, TimeoutException):
		return None

def moodle_html(headless=False):
	options = Options()
	if headless:
		options.add_argument("--headless")
	options.add_argument("--user-data-dir=broswer-data")
	driver = webdriver.Chrome(options=options)
	
	try:
		driver.get(URL)
		if not load_session_state(driver, browserStatePath):
			print("No session state found")
		else:
			print("Session state loaded")

		# Refresh page to load session
		driver.refresh()
		print("Opened moodle")

		# Check if user is already logged in
		timeline = check_if_logged_in(driver)

		if not timeline:
			driver.get("https://moodle.hku.hk/login/index.php?authCAS=CAS")
		else:
			return timeline

		while driver.current_url != URL:
			if driver.current_url == "https://hkuportal.hku.hk/cas/aad":
				WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login_btn")))
				driver.find_element(By.ID, "email").send_keys(USERNAME)
				driver.find_element(By.ID, "login_btn").click()
				# WebDriverWait(driver, 10).until(EC.url_contains("adfs.connect.hku.hk"))
			elif "adfs.connect.hku.hk" in driver.current_url:
				WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "passwordInput")))
				driver.find_element(By.ID, "passwordInput").send_keys(PASSWORD)
				driver.find_element(By.ID, "submitButton").click()
			elif "login.microsoftonline.com" in driver.current_url:
				WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "idSIButton9")))
				driver.find_element(By.ID, "idSIButton9").click()
			else:
				print(f"Unknown page ({driver.current_url}), please login manually if not redirected to Moodle")
				if headless:
					raise Exception("Login expired!")
				print("Press Enter after you have successfully logged in and can see the dashboard")
				input()
		
		# Check if logged in and get timeline
		timeline = check_if_logged_in(driver)
		if timeline is not None:
			return timeline
		else:
			print("Login verification failed. Please try again.")
			return None
	except Exception as e:
		print("Error occurred:", e)
		if not headless: input("Press Enter to close browser...")
	finally:
		driver.quit()

def get_moodle_dealines(headless=True):
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

		due_time = event.select('small')[0].text.strip()


		event_ = event.find('a')
		link = event_.attrs['href']
		id = link.split("?id=")[1]
		title = event_.text.strip()
		course = event.select('small')[1].text.split("·")[1].strip()
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
