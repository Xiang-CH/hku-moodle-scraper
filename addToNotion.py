import dotenv
import os
from notion_client import Client, APIResponseError
from pprint import pprint
import logging
from getEvents import get_moodle_dealines
from datetime import datetime
import pytz

import argparse
import sys
from typing import Any, Dict

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
dotenv.load_dotenv()
DB_ID = os.getenv("NOTION_DATABASE_ID")

def create_db(notion):
	try:
		res = notion.databases.create(
			parent={"type": "page_id", "page_id": os.getenv("NOTION_PAGE_ID")},
			title=[{"text": {"content": "Task List"}}],
			icon={"type": "emoji", "emoji": "📥"},
			is_inline=True,
			properties={
				"Done": {
					"checkbox": {}
				},
				"Title": {
					"title": {}
				},
				"Course": {
					"rich_text": {}
				},
				"Course Code": {
					"select": {}
				},
				"Due Date": {
					"date": {}
				},
				"Tags": {
					"multi_select": {}
				},
				"Link": {
					"url": {}
				}
			}
		)
		print("Database created")
		DB_ID = res["id"]
		dotenv.set_key('.env', "NOTION_DATABASE_ID", DB_ID)
		os.environ["NOTION_DATABASE_ID"] = DB_ID
	except APIResponseError as error:
		logging.error(error)
		return None

def get_db(notion):
	if DB_ID is None:
		create_db(notion)
		return None

	filter_params = {
		"property": "Due Date",
		"date": {
			"on_or_after": datetime.now(pytz.timezone("Asia/Shanghai")).isoformat()
		}
	}
	try:
		db = notion.databases.query(
			**{"database_id": DB_ID,
			   "filter": filter_params})
		# pprint(db)
		return db
	except APIResponseError as error:
		logging.error(error)


def event_to_notion_page_properties(event: Dict[str, Any]) -> Dict[str, Any]:
	title = event["title"].split('is due')[0].strip()
	if not "Due" in title and not "Deadline" in title:
		title += " (Due: " + event["due_time"]+ ")"
	return {
		"Title": {
			"title": [
				{"text": {
					"content": title
				}}
			]
		},
		"Due Date": {"date": {"start": datetime.fromtimestamp(event["time_stamp"], pytz.timezone(zone='Asia/Shanghai')).date().isoformat()}},
		"Course Code": {"select": {"name": event["course"].split(" ")[0]}},
		"Course": {"rich_text": [{
			"type": "text",
			"text": {
				"content": event["course"].split(" ", 1)[1].split("[")[0].strip(),
				"link": None
			},
		}]},
		"Link": {"url": event["link"]},
		"Tags": {"multi_select": [{"name": "Assignment"}]},
		"Done": {"checkbox": False}
	}


def add_to_notion(event, notion):
	DB_ID = os.getenv("NOTION_DATABASE_ID")
	try:
		res = notion.pages.create(
			parent={"database_id": DB_ID},
			properties=event_to_notion_page_properties(event)
		)
		# pprint(res)
	except APIResponseError as error:
		print(error)
		logging.error(error)


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Fetch Moodle deadlines and add them to a Notion database.")
	group = parser.add_mutually_exclusive_group()
	group.add_argument(
		"--headless",
		dest="headless",
		action="store_true",
		help="Run browser in headless mode (default).",
	)
	parser.set_defaults(headless=False)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	headless = args.headless

	notion_token = os.getenv("NOTION_TOKEN")
	if not notion_token:
		logging.error("NOTION_TOKEN is not set. Please set it in your environment or .env file.")
		return 1

	notion = Client(auth=notion_token)

	# Fetch existing DB to dedupe by Link URL
	db = get_db(notion)
	exit_event_urls = [] if db is None else [obj["properties"]["Link"]["url"] for obj in db.get('results', [])]

	# Fetch Moodle deadlines
	try:
		events = get_moodle_dealines(headless=headless)
	except Exception as e:
		logging.error("Failed to fetch Moodle deadlines: %s", e)
		if headless:
			logging.info("If your Moodle session expired, re-run without headless mode to login manually.")
		return 1

	if not events:
		logging.info("No events found to add.")
		return 0

	# Add new events only
	added_count = 0
	for event in events:
		if event.get("link") in exit_event_urls:
			continue
		add_to_notion(event, notion)
		logging.info("Added to Notion: %s", event.get("title"))
		added_count += 1

	logging.info("Completed. %d new event(s) added.", added_count)
	return 0


if __name__ == "__main__":
	sys.exit(main())
