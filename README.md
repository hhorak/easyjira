# easyjira
Jira cmd-line tool that looks like python bugzilla

## Jira Token
- Jira token can be obtained by opening your Jira profile in the "Personal Access Tokens" section
- Token can be supplied in 3 ways:
  - In python keyring for service https://issues.redhat.com and username token
  - In a file inside your home folder: `$HOME/.config/jira/easyjira`
  - Saved in an environment variable `JIRA_TOKEN=<TOKEN>`
- Provide only the token string and nothing else (your email or any other information is not needed)

Use ``easyjira access --configure [--keyring]`` for simple configuration.
Use ``python -m keyring.cli`` to manage the keyring.

## Usage

```
usage: easyjira [-h] [--show-api-calls] [--store-api-calls STORE_API_CALLS] [--simulate] [--debug]
                {query,new,update,clone,move,fields-mapping,access} ...

Work with JIRA from cmd-line like you liked doing it with python-bugzilla-cli.
------------------------------------------------------------------------------
  When working with the tool, check what fields exist in a project you work with.
  Jira is masively configurable, so many fields are available under customfield_12345 name.
  This tool is supposed to hide some of the specifics and is supposed to be an opiniated
  tool for RHEL project specifically.

  Another motivation for this tool is to help people working with Jira API to learn
  the concepts easily, by showing how several basic operations done via CLI would
  look like in a Python script (see the --simulate argument).

  Query JIRA issues:
    You can query issues by ID, JQL or URL (from which we usually extract JQL anyway).
    For stored filters, you can easily use filter=<i> as JQL or part of JQL.
    Results are paginated.

    Examples:
      easyjira query --jql 'project = RHELPLAN' --max_results 100 --start_at 200
      easyjira query --from-url 'https://issues.redhat.com/issues/?jql=project%20%3D%20%22RHEL%20Planning%22%20and%20issueLinkType%20%3D%20clones%20'
      easyjira query --jql 'parent = RHELPLAN-138763' --outputformat '{key}'
      easyjira --simulate query --jql 'filter=12363088'

  Updating JIRA issues:
    Consider reading "Updating an Issue via the JIRA REST APIs" section of the Jira API:
    https://developer.atlassian.com/server/jira/platform/updating-an-issue-via-the-jira-rest-apis-6848604/

    Examples:
      easyjira update -j RHELPLAN-95816 --json '{"fields": { "summary": "rebuild of nodejs-12-container 8.4.z" } }'
      easyjira update -j RHELPLAN-95816 --json '{"update": { "labels": [ {"add": "mynewlabel"} ] } }'
      easyjira update -j RHELPLAN-95816 --json '{"update": { "labels": [ {"remove": "mynewlabel"} ] } }'
      easyjira update -j RHELPLAN-142727 --json '{"update": {"issuelinks": [{"add": {"outwardIssue": {"key": "RHELPLAN-141789"}, "type": {"inward": "is cloned by", "name": "Cloners", "outward": "clones"}}}]}}'

    Notes:
      Changing the issue type to sub-task seems to be not possible: https://jira.atlassian.com/browse/JRASERVER-33927

  Creating JIRA issues:
    Pick a project (RHEL is the default), specify summary and description and create an issue.

    Examples:
      easyjira new --summary 'Test issue for playing around with Jira API' --description 'testing description with a nice text simulating a text for a <bug> or a <feature>.'  --project RHELPLAN

  Moving to a different status and closing JIRA issues:
    Closing a JIRA issue is just a move to a different status.

    Examples:
      easyjira move -j RHELPLAN-141789 --status Closed --resolution 'Not a Bug' --comment 'closing'

  Cloning a Jira issue:
    This is similar to creating, the specified issue is fetched first, then we pick several fields to keep.

    Examples:
      # Clone an issue with no changes
      easyjira clone -j RHELPLAN-141789

      # Clone an issue and set different issue type and change description using regexp
      easyjira clone -j RHELPLAN-141789 --set '{"issuetype": {"name": "Feature"}}' --re '{"description": {"pattern": "issue", "replacement": "bug"}}'

      # clone RHEL 8 PRP template
      easyjira clone  -j RHELPLAN-27509  --re '{"summary": {"pattern": "<package_name>", "replacement": "newfakecomponent"}, "description": [{"pattern": "<package_name>", "replacement": "newfakecomponent"}, {"pattern": "<the package to add>", "replacement": "newfakecomponent"}, {"pattern": "<a bugzilla bug ID>", "replacement": "12345678fake"}]}'
      easyjira clone  -j RHELPLAN-27509  --re '{"summary": {"pattern": "<package_name>", "replacement": "newfakecomponent"}}' --set '{"description": "{noformat}\nDISTRIBUTION BUG: 12345fake\nPACKAGE NAME: newfakecomponent\nPACKAGE TYPE: standalone\nPRODUCT: Red Hat Enterprise Linux 8\nPRODUCT VERSION: 8.8.0\nBUGZILLA REQUESTER: fakedevel@redhat.com\nACG LEVEL: 4\nQE CONTACT KERBEROS ID: fakeqe\nQE CONTACT RED HAT JIRA USERNAME: fakeqe@redhat.com\nQE CONTACT BUGZILLA: rhel-fake-subsystem-qe@redhat.com\nQE CONTACT IS A USER: NO\nUSER KERBEROS ID: fakedevel\nRED HAT JIRA USERNAME: fakedevel@redhat.com\nBUGZILLA ACCOUNT: fakedevel@redhat.com\n{noformat}"}'

      # Clone an issue and add a suffix to the summary
      easyjira clone  -j RHELPLAN-141789  --re '{"summary": {"pattern": "$", "replacement": " cloned"}}'

      # Clone one issue linked to an epic and assign it to a different team
      cat teams2clone | while read -r team ; do echo $team ; easyjira clone -j RHELMISC-18238 --re "{\"summary\": {\"pattern\": \"rhel-pt-pcp\", \"replacement\": \"$team\"}}" --set "{\"AssignedTeam\": \"$team\"}" ; sleep 3 ; done

positional arguments:
  {query,new,update,clone,move,fields-mapping,access}
                        commands
    query               query JIRA issues
    new                 create a new JIRA issue
    update              update a JIRA issue
    clone               clone a JIRA issue
    move                change a JIRA issue status
    fields-mapping      show fields mapping for a project and issue type (shows only fields available when creating a new issue) or
                        specific issue (shows all fields)
    access              verifies that the tool is able to access the server

options:
  -h, --help            show this help message and exit
  --show-api-calls      Show what API calls the tool performed and with what input. The output is printed to stderr.
  --store-api-calls STORE_API_CALLS
                        Store what API calls the tool performed and with what input into a given file. The data are appeneded.
  --simulate            Do not proceed with any API calls.
  --debug               Show very verbose log of what the tool does.

```
