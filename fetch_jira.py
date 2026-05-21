import os, json, base64, urllib.request, urllib.parse
from datetime import datetime, timezone

DOMAIN  = os.environ["JIRA_DOMAIN"].strip()
EMAIL   = os.environ["JIRA_EMAIL"].strip()
TOKEN   = os.environ["JIRA_TOKEN"].strip()
ACCOUNT = os.environ["JIRA_ACCOUNT_ID"].strip()
AUTH    = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()

def search(jql, fields, max_results=50):
    url  = f"https://{DOMAIN}/rest/api/3/search/jql"
    body = json.dumps({"jql": jql, "fields": fields, "maxResults": max_results}).encode()
    req  = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"Basic {AUTH}",
        "Content-Type":  "application/json"
    })
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["issues"]

def to_issue(i):
    f     = i["fields"]
    subs  = f.get("subtasks") or []
    done  = sum(1 for s in subs if s["fields"]["status"]["statusCategory"]["key"] == "done")
    return {
        "key":       i["key"],
        "summary":   f["summary"],
        "statusCat": f["status"]["statusCategory"]["key"],
        "status":    f["status"]["name"],
        "duedate":   f.get("duedate"),
        "subtasks":  {"done": done, "total": len(subs)}
    }

FIELDS = ["summary", "status", "subtasks", "duedate"]
L = f'project=LWVR AND issuetype="TASK _ SC" AND assignee="{ACCOUNT}"'
Z = f'project=ZOPS AND assignee="{ACCOUNT}"'

data = {
    "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
    "lwvr": {
        "inprogress": [to_issue(i) for i in search(f'{L} AND statusCategory="In Progress" ORDER BY duedate ASC', FIELDS)],
        "todo":       [to_issue(i) for i in search(f'{L} AND statusCategory="To Do" AND duedate<=14d ORDER BY duedate ASC', FIELDS)],
        "done":       [to_issue(i) for i in search(f'{L} AND statusCategory=Done ORDER BY updated DESC', FIELDS, 100)]
    },
    "zops": {
        "inprogress": [to_issue(i) for i in search(f'{Z} AND statusCategory="In Progress" ORDER BY duedate ASC', FIELDS)],
        "todo":       [to_issue(i) for i in search(f'{Z} AND statusCategory="To Do" AND duedate<=14d ORDER BY duedate ASC', FIELDS)],
        "done":       [to_issue(i) for i in search(f'{Z} AND statusCategory=Done ORDER BY updated DESC', FIELDS, 100)]
    }
}

with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"완료: LWVR {len(data['lwvr']['inprogress'])}개 진행중 / ZOPS {len(data['zops']['inprogress'])}개 진행중")