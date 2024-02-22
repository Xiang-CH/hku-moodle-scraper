# HKU Moodle Events to Notion Database

This scrapper script retreives user's HKU Moodle Events (Assignments Deadlines), and auto update the events on a Notion Database.

![1708618894109](image/README/1708618894109.png)

##### Step 1

Create an .env file and fill in your **HKU email** and **Portal PIN number**. You will also need your **Notion Token** and The **Notion Page ID** depending on where you want to place the database

```bash
#.env
USER_NAME = ""
PASSWORD = ""
NOTION_TOKEN = ""
NOTION_PAGE_ID = ""
```

* To find your Notion Token goto: https://www.notion.so/my-integrations   Create an new intergration and copy the **Internal Integration Secret**

![1708616785539](image/README/1708616785539.png)

![1708616871762](image/README/1708616871762.png)

To find the Page ID of your desired Notion Page, go to the page and copy its link![1708617234304](image/README/1708617234304.png)

* E.g. The page_id of https://www.notion.so/chen-xiang/Test-fd292c99909f46e3b5ad3c3164a9213b?pvs=4 is fd292c99909f46e3b5ad3c3164a9213b
* Also remember to Connect your page to your intergration

![1708617434380](image/README/1708617434380.png)

##### Step 2

* Run the script using:

  ```shell
  ./run.sh
  ```
