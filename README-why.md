Why this project exists
=======================

You know it -- 14 competing standards and none is good enough... 

![14 competing standards xkcd](https://imgs.xkcd.com/comics/standards_2x.png)

Yes, yes, I admit this is yet another tool that tries to work with Jira API with some universal way, but hold your horses, hear this story:

Imagine me being a developer who wanted to script some repeating work in Jira and also was familiar with python-bugzilla -- that tool allowed me to use it efficiently because I already knew the interface, fields, and it behaved pretty intuitively. Adding a blocker to various trackers, commenting or closing several bugs was therefore a matter of a minute if I had bug IDs at hand:

```
bugzilla modify -l "Approving for release" -f devel_ack+ 123456 7890123 345678
bugzilla modify --close WONTFIX -l "Not a priority"
etc..
```

Story
-----

Now, when adopting Jira as the issue tracker platform for RHEL, I don't want to loose this ability.

Yes, Jira webUI is able to edit several issues at once, but sometimes I want to connect the work with some more Bash scripting, or write some more advanced python script to make the work for me.

When looking at existing jira CLI tools, I didn't find one that would be simple and universal enough, and also would work with the Jira instance issues.redhat.com that we use. The RestAPI looked easy enough to be used with a token, but I soon found traps like status change is actually a transition, or need to have data in JSON format, which is not that easy to generate in Bash.

Anyway, somewhere at this point I realized that I might create a new tool, that would help me to do both -- access Jira from a command-line (or Bash script) and if I'd need to write something more complex, the tool could help me to figure out how RestAPI calls look like.

To show this power, let's say I want to clone one issue, change the summary with a regular expression replacement and then close it. Try yourself how much time you spend on reading the Jira API documentation to make this happen. And now see how easy it can be achieved and that the tool might help you generate some python snippets that you can re-use for a more mature script:

```
$ easyjira --store-api-calls /tmp/apicalls.py clone  -j RHELPLAN-141789  --re '{"summary": {"pattern": "$", "replacement": " cloned for testing"}}'
RHELPLAN-158807

$ easyjira --store-api-calls /tmp/apicalls.py move -j RHELPLAN-158807 --status "In Progress" --comment 'Moving to In progress'
Issue RHELPLAN-158807 moved to In Progress.
Comment added to the issue RHELPLAN-158807.

$ easyjira --store-api-calls /tmp/apicalls.py update  --link-type blocks --link-issue RHELPLAN-141789 -j RHELPLAN-158807 --comment 'adding a blocking link'
Issue RHELPLAN-158807 updated.

$ easyjira --store-api-calls /tmp/apicalls.py move -j RHELPLAN-158807 --status Closed --resolution 'Not a Bug' --comment 'closing, not needed actually'
Issue RHELPLAN-158807 moved to Closed.
Comment added to the issue RHELPLAN-158807.
```

And you can then check the API calls done during the way (blank lines added for better readability):

```
$ cat /tmp/apicalls.py

#!/usr/bin/env python3
# Python 3 snippets that may help you write your script, do not use without proper review
import requests, pprint
headers = {'Accept': 'application/json', 'Authorization': 'Bearer {token}'}

params = None
response = requests.get("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-141789", params=params, headers=headers)
pprint.pprint(response.json())

json = {'fields': {'summary': 'REST ye merry gentlemen. cloned for testing', <snipped>}}
response = requests.post("https://issues.redhat.com/rest/api/2/issue", json=json, headers=headers)
pprint.pprint(response.json())


#!/usr/bin/env python3
# Python 3 snippets that may help you write your script, do not use without proper review
import requests, pprint
headers = {'Accept': 'application/json', 'Authorization': 'Bearer {token}'}

params = None
response = requests.get("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-158807/transitions?expand=transitions.fields", params=params, headers=headers)
pprint.pprint(response.json())

json = {'transition': {'id': '21'}}
response = requests.post("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-158807/transitions", json=json, headers=headers)
pprint.pprint(response.json())

json = {'body': 'Moving to In progress'}
response = requests.post("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-158807/comment", json=json, headers=headers)
pprint.pprint(response.json())


#!/usr/bin/env python3
# Python 3 snippets that may help you write your script, do not use without proper review
import requests, pprint
headers = {'Accept': 'application/json', 'Authorization': 'Bearer {token}'}

json = {'update': {'issuelinks': [{'add': {'type': {'name': 'Blocks', 'inward': 'is blocked by', 'outward': 'blocks'}, 'outwardIssue': {'key': 'RHELPLAN-141789'}}}]}}
response = requests.put("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-158807", json=json, headers=headers)
pprint.pprint(response.json())


#!/usr/bin/env python3
# Python 3 snippets that may help you write your script, do not use without proper review
import requests, pprint
headers = {'Accept': 'application/json', 'Authorization': 'Bearer {token}'}

params = None
response = requests.get("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-158807/transitions?expand=transitions.fields", params=params, headers=headers)
pprint.pprint(response.json())

json = {'transition': {'id': '221'}, 'fields': {'resolution': {'name': 'Not a Bug'}}}
response = requests.post("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-158807/transitions", json=json, headers=headers)
pprint.pprint(response.json())

json = {'body': 'closing, not needed actually'}
response = requests.post("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-158807/comment", json=json, headers=headers)
pprint.pprint(response.json())

```

Unique value
------------
And this is the unique value I see in this tool -- being it a learning tool, something that should help somebody who is new to Jira RestAPI to figure out what Python code should look like to achieve some basic actions. That should make writing some ad-hoc Python script to handle something more complex much more effective.

No-goals
--------
What I'd like to avoid is somebody using the tool as a dependency of something. There is likely not much value other than some API calls anyway, but more importantly, I don't plan to maintain backward compatibility. I only recommend to use the tool for ad-hoc work or as the learning tool.

Enjoy it and feel free to provide feedback or contributions if you like.
