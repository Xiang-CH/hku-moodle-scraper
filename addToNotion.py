import dotenv
import os
from notion_client import Client, APIResponseError
from pprint import pprint
import logging
from getEvents import get_moodle_dealines
from datetime import datetime
import pytz

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


def event_to_notion_page_properties(event):
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


def main():
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    db = get_db(notion)
    exit_event_urls = [] if db == None else [obj["properties"]["Link"]["url"] for obj in db['results']]
    events = get_moodle_dealines()
    for event in events:
        if event["link"] in exit_event_urls:
            continue
        add_to_notion(event, notion)
        print(f"{event['title']} added to Notion.")
        # pprint(property)


if __name__ == "__main__":
    main()
