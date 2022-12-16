#!/bin/env python3

import argparse
import os
import requests
import sys
import codecs # for decoding escapte characters
import urllib
import pprint
import json
import textwrap

JIRA_PROJECTS_URL = "https://issues.redhat.com"
JIRA_REST_URL = f"{JIRA_PROJECTS_URL}/rest/api/2"
DEFAULT_MAX_RESULTS = 20

DEFAULT_OUTPUT="{key}"

def error(message):
    print(message)
    exit(1)

def get_token() -> str:
    try:
        token = os.environ['JIRA_TOKEN']
    except KeyError:
        error("JIRA_TOKEN environment variable missing, create one in Jira UX")
    return token

def get_auth_data() -> dict:
    token = get_token()
    auth = {
            "Accept": "application/json",
            "Authorization": "Bearer " + token
           }
    return auth

def get_headers() -> dict:
    return get_auth_data()

# TODO:
def _log_request(url, method, params):
    pass

def _print_issue(output_format, issue):
    print(output_format.format(**issue))

def _print_issues(output_format, issues):
    for issue in issues:
        _print_issue(output_format, issue)

def _print_raw_issues(issues):
    print(json.dumps(issues, sort_keys=True, indent=4))

def get_file_content(filename):
    with open(filename) as f:
        return f.readlines()

def _get_issue(issue, headers=None):
    if not headers:
        headers = get_headers()

    r = requests.get(f"{JIRA_REST_URL}/issue/{issue}", headers=headers)
    return r.json()

def get_fields_mapping(project, issue_type, only_required=False):
    mapping = {}
    headers = get_headers()
    r = requests.get(f"{JIRA_REST_URL}/issue/createmeta?projectKeys={project}&issuetypeNames={issue_type}&expand=projects.issuetypes.fields", headers=headers)
    data = r.json()
    try:
        for key in data['projects'][0]['issuetypes'][0]['fields']:
            if data['projects'][0]['issuetypes'][0]['fields'][key]['required'] or not only_required:
                mapping[key] = data['projects'][0]['issuetypes'][0]['fields'][key]['name']
    except IndexError:
        error(f'Data not found. It is possible that project {project} has no issue type {issue_type}.')
    return mapping

def get_jql_from_url(url) -> str:
    url_parsed = urllib.parse.urlparse(url)
    jql = ''
    if url_parsed.query != '':
        for url_query in urllib.parse.parse_qsl(url_parsed.query):
            if url_query[0] == 'filter' and len(url_query) == 2:
                jql = 'filter={}'.format(url_query[1])
            elif url_query[0] == 'jql' and len(url_query) == 2:
                # not sure how we can only encode the value
                jql = url_query[1]
    return jql

def cmd_fields_mapping(args):
    mapping = get_fields_mapping(args.project, args.issue_type, args.only_required)
    print(json.dumps(mapping, sort_keys=True, indent=4))

def cmd_query(args):
    output=[]
    
    # get issues based on ID
    headers = get_headers()
    if args.id:
        for issue in args.id:
            output.append(_get_issue(issue, headers=headers))
            #r=requests.get(f"{JIRA_REST_URL}/issue/{issue}", headers=headers)
            #output.append(r.json())

    # get issues based on url with a query
    if args.from_url:
        args.jql = get_jql_from_url(args.from_url)
    #r=requests.post(f"{JIRA_REST_URL}/search", json=args.from_url, headers=headers, verify=False)
    #output.append(r.json())

    # get issues based on jql only
    if args.jql:
        query = urllib.parse.urlencode([('jql',args.jql), ('maxResults', args.max_results), ('startAt', args.start_at)])
        r=requests.get(f"{JIRA_REST_URL}/search", params=query, headers=headers)
        if r.ok:
            output += r.json()['issues']

    if args.output_format:
        # use codecs to interpret escape characters
        output_format = codecs.escape_decode(bytes(args.output_format, "utf-8"))[0].decode("utf-8")
    else:
        output_format = DEFAULT_OUTPUT

    if args.raw:
        _print_raw_issues(output)
    else:
        _print_issues(output_format, output)

def _create_issue(input_data, args):
    headers = get_headers()
    r=requests.post(f"{JIRA_REST_URL}/issue", json=input_data, headers=headers)
    if not r.ok:
        print(r.text)
        error('Issue NOT created.')
    new_issue = r.json()
    # TODO: we can re-load the whole issue again to allow show other fields than key and id
    #pprint.pprint(new_issue)
    if args.output_format:
        # use codecs to interpret escape characters
        output_format = codecs.escape_decode(bytes(args.output_format, "utf-8"))[0].decode("utf-8")
    else:
        output_format = DEFAULT_OUTPUT

    if args.raw:
        _print_raw_issues(new_issue)
    else:
        _print_issue(output_format, new_issue)

def cmd_create(args):
    """
    We need to get some JSON structure like this:
    {
       "fields": {
          "project":
          {
             "key": "TEST"
          },
          "summary": "REST ye merry gentlemen.",
          "description": "Creating of an issue using project keys and issue type names using the REST API",
          "issuetype": {
             "name": "Bug"
          }
       }
    }
    """
    headers = get_headers()
    mapping = get_fields_mapping(args.project, args.issue_type, True)
    if args.json:
        input_data = json.loads(args.json)
    elif args.json_file:
        input_data = json.load(args.json_file)
    else:
        input_fields = {'project': {'key': args.project}, 'issuetype': {'name': args.issue_type}}
        if not args.summary:
            error("Summary field is compulsory")
        input_fields['summary'] = args.summary
        if (args.description and args.description_file):
            error("Specify either --description or --description_file, but not both")
        input_fields['description'] = args.description or get_file_content(args.description_file)
        input_data = {'fields': input_fields}
    print(json.dumps(input_data, sort_keys=True, indent=4))
    _create_issue(input_data, args)

def _update_issue(issue, query):
    headers = get_headers()
    r = requests.put(f"{JIRA_REST_URL}/issue/{issue}", json=query, headers=headers)
    if r.ok:
        print(f'Issue {issue} updated.')
    else:
        print(f'ERROR: Issue {issue} NOT updated.')
        print(dir(r))
        pprint.pprint([r.reason, r.text, r.raw])

def cmd_update(args):
    """
    How Bugzilla CLI approached special fields:
    Fields that take multiple values have a special input format.
    Append:    --cc=foo@example.com
    Overwrite: --cc==foo@example.com
    Remove:    --cc=-foo@example.com
    Options that accept this format: --cc, --blocked, --dependson,
        --groups, --tags, whiteboard fields.

    What we expect in Jira:
        <...> --json ' { "fields": { "summary": "rebuild of nodejs-12-container 8.4" } }'
        <...> --json ' {"update": { "labels": [ {"add": "mynewlabel"} ] } }'
        <...> --json ' {"update": { "labels": [ {"remove": "mynewlabel"} ] } }'

    query={"update":{"labels":[{"add":"jira-bugzilla-resync"}]}}
    r=requests.put(f"{JIRA_REST_URL}/issue/RHELPLAN-95816", json=query, headers=headers, verify=False)
    """
    headers = get_headers()
    query = json.loads(args.json)
    if args.id:
        for issue in args.id:
            print(f'Issue {issue} being updated with: {query}')
            _update_issue(issue, query)

def cmd_clone(args):
    """
    Clone an issue with some logic for keeping, changing and removing some specific fields.
    """
    headers = get_headers()
    issue = args.id
    original = _get_issue(issue, headers=headers)
    original_fields = original['fields']
    input_fields = {}
    input_fields['summary'] = original_fields['summary']
    input_fields['description'] = original_fields['description']
    input_fields['project'] = original_fields['project']
    input_fields['issuetype'] = original_fields['issuetype']
    clon_data = {'fields': input_fields}
    _create_issue(clon_data, args)
    #pprint.pprint(clon)


def _get_transitions(issue):
    headers = get_headers()
    r = requests.get(f"{JIRA_REST_URL}/issue/{issue}/transitions?expand=transitions.fields", headers=headers)
    if r.ok:
        return r.json()['transitions']


def _filter_transition_id(issue, status, resolution):
    result = {}
    transitions = _get_transitions(issue)
    for t in transitions:
        if t['name'] == status:
            result['transition'] = {'id': t['id']}
            # just for status, check the given resolution is valid
            if status == 'Closed' and 'resolution' in t['fields']:
                for r in t['fields']['resolution']['allowedValues']:
                    if r['name'] == resolution:
                        result['fields'] = {'resolution': {'name': resolution}}
            return result
    error(f"Cannot find a transition called '{status}' for issue '{issue}'")


def cmd_move(args):
    """
    Move an issue to a different status with some comment and resolution if exists for the target status.
    This requires transition id probably: https://issues.redhat.com/rest/api/2/issue/RHELPLAN-141790/transitions?expand=transitions.fields
    https://community.atlassian.com/t5/Jira-questions/Close-Jira-Issue-via-REST-API/qaq-p/1845399
    """
    headers = get_headers()
    if (args.comment and args.comment_file):
        error("Specify either --comment or --comment_file, but not both")
    issue = args.id
    status = args.status
    input_data = _filter_transition_id(issue, status, args.resolution)
    r = requests.post(f"{JIRA_REST_URL}/issue/{issue}/transitions", json=input_data, headers=headers)
    if r.ok:
        print(f'Issue {issue} moved to {status}.')
    else:
        print(f'ERROR: Issue {issue} NOT transitioned.')
        print(r.text)
    if args.comment or args.comment_file:
        comment_data = {'body': args.comment or get_file_content(args.comment_file)}
        r = requests.post(f"{JIRA_REST_URL}/issue/{issue}/comment", json=comment_data, headers=headers)
        if r.ok:
            print(f'Comment added to the issue {issue}.')
        else:
            print(f'ERROR: Comment not added to the tissue {issue}.')
            print(r.text)


def main() -> int:
    """Main program entry that parses args"""
    program_name = 'bzjira'
    description=textwrap.dedent('''\
        Work with JIRA from cmd-line like you liked doing it with python-bugzilla-cli.
        ------------------------------------------------------------------------------
          When working with the tool, check what fields exist in a project you work with.
          Jira is masively configurable, so many fields are available under customfield_12345 name.

          Query JIRA issues:
            You can query issues by ID, JQL or URL (from which we usually extract JQL anyway).
            For stored filters, you can easily use filter=<i> as JQL or part of JQL.
            Results are paginated.

            Examples:
              {program_name} query --jql 'project = RHELPLAN' --max_results 100 --start_at 200
              {program_name} query --from-url 'https://issues.redhat.com/issues/?jql=project%20%3D%20%22RHEL%20Planning%22%20and%20issueLinkType%20%3D%20clones%20'
              {program_name} query --jql 'filter=12363088'

          Updating JIRA issues:
            Consider reading "Updating an Issue via the JIRA REST APIs" section of the Jira API:
            https://developer.atlassian.com/server/jira/platform/updating-an-issue-via-the-jira-rest-apis-6848604/

            Examples:
              {program_name} update -j RHELPLAN-95816 --json ' { "fields": { "summary": "rebuild of nodejs-12-container 8.4.z" } }'
              {program_name} update -j RHELPLAN-95816 --json ' {"update": { "labels": [ {"add": "mynewlabel"} ] } }'
              {program_name} update -j RHELPLAN-95816 --json ' {"update": { "labels": [ {"remove": "mynewlabel"} ] } }'

          Creating JIRA issues:
            Pick a project (RHEL is the default), specify summary and description and create an issue.

            Examples:
              {program_name} new --summary 'Test issue for playing around with Jira API' --description 'testing description with a nice text simulating a text for a <bug> or a <feature>.'  --project RHELPLAN

          Moving to a different status and closing JIRA issues:
            Closing a JIRA issue is just a move to a different status.

            Examples:
              {program_name} move -j RHELPLAN-141789 --status Closed --resolution 'Not a Bug' --comment 'closing'

          Cloning a Jira issue:
            This is similar to creating, the specified issue is fetched first, then we pick several fields to keep.

            Examples:
              {program_name} clone -j RHELPLAN-141789
        ''')
    # do not expand anything else than the program name, complicated format
    # would make issues when using f-strings or .format()
    description=description.replace('{program_name}', program_name)
    parser = argparse.ArgumentParser(prog=program_name, description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    subparsers = parser.add_subparsers(help='commands')
    parser.add_argument('--show-api-calls', action='store_true', help='Show what API calls the tool performed and with what input. The output is printed to stderr.')
    parser.add_argument('--simulate', action='store_true', help='Do not proceed with the API calls, only show what the tool would do.')
    parser.add_argument('--debug', action='store_true', help='Show very verbose log of what the tool does.')

    # query command
    parser_query = subparsers.add_parser('query', help='query JIRA issues')
    parser_query.add_argument('-j', '--id', '--jira_id', metavar='ID', type=str, nargs='+',
                              help='Jira issues ID')
    parser_query.add_argument('--from-url', dest='from_url',
                        help='Use full URL as an argument')
    parser_query.add_argument('--jql', dest='jql',
                        help='Use JQL query')
    parser_query.add_argument('--raw', action='store_true',
                        help='Display raw issue data (JSON)')
    parser_query.add_argument('--start_at', dest='start_at', default=0, help='Pagination, start at which item in the output of a single query')
    parser_query.add_argument('--max_results', dest='max_results', default=DEFAULT_MAX_RESULTS, help='Pagination, how many items in the output of a single query, not counting individually requested IDs')

    # the idea here is to use something like print("format from user".format(**issue)) but needs to be validated by some real pythonist for security
    parser_query.add_argument('--outputformat', dest='output_format',
                        help='Print output in the form given. Use str.format string with {key} or {field["duedate"]} syntax. Use --raw to see what keys exist.')
    parser_query.set_defaults(func=cmd_query)

    # new command
    parser_new = subparsers.add_parser('new', help='create a new JIRA issue')
    parser_new.set_defaults(func=cmd_create)
    parser_new.add_argument('--json', action='store_true',
                            help='Input raw issue data (JSON)')
    parser_new.add_argument('--json_file',
                            help='Input raw issue data from a JSON file')
    parser_new.add_argument('--project', default='RHEL', help='Which project to show fields for (default RHEL)')
    parser_new.add_argument('--issue_type', default='Bug', help='Which issue type do we want to see fields for (default Bug)')
    parser_new.add_argument('--summary', help='A short summary of the issue (must be set if we specify fields separately)')
    parser_new.add_argument('--description', help='Longer description of the issue (either this or description_file must be set if we specify fields separately)')
    parser_new.add_argument('--description_file', help='Longer description of the issue located in a file (either this or description must be set if we specify fields separately)')
    parser_new.add_argument('--link-subtask', help='Add a link to sub-task issue')
    parser_new.add_argument('--link-parent', help='Add a link to the parent issue')
    parser_new.add_argument('--link-epic', help='Add an epic to the new issue')
    parser_new.add_argument('--raw', action='store_true',
                        help='Display raw issue data (JSON)')
    parser_new.add_argument('--outputformat', dest='output_format',
                        help='Print output in the form given. Use str.format string with {key} or {field["duedate"]} syntax. Use --json to see what keys exist.')

    # update command
    parser_update = subparsers.add_parser('update', help='update a JIRA issue')
    parser_update.set_defaults(func=cmd_update)
    parser_update.add_argument('-j', '--id', '--jira_id', metavar='ID', type=str, nargs='+',
                               help='Jira issues ID')
    parser_update.add_argument('--json', metavar='json', type=str, required = True,
                               help='JSON that defines what should be changed. See "Updating an Issue via the JIRA REST APIs" section of the Jira API: https://developer.atlassian.com/server/jira/platform/updating-an-issue-via-the-jira-rest-apis-6848604/')
    parser_update.add_argument('--comment', help='Longer comment to be added to the issue')
    parser_update.add_argument('--comment_file', help='Longer comment to be added to issue located in a file')

    # clone command
    parser_clone = subparsers.add_parser('clone', help='clone a JIRA issue')
    parser_clone.set_defaults(func=cmd_clone)
    parser_clone.add_argument('-j', '--id', '--jira_id', metavar='ID', type=str, required = True,
                               help='Jira issues ID')
    parser_clone.add_argument('--keep', metavar='key', type=str,
                               help='name of the key to keep in the clone (by default, keys kept are summary, description, labels)')
    parser_clone.add_argument('--remove', metavar='key', type=str,
                               help='name of the key to remove from the clon (by default, keys kept are summary, description, labels)')
    parser_clone.add_argument('--set', metavar='json', type=str,
                               help='JSON that defines what should be changed by replacing the content entirely. Example: {"summary": "My new summary"}')
    parser_clone.add_argument('--re', metavar='json', type=str,
                               help='JSON that defines what should be changed using regexp. The value must be a dict with keys pattern and replacement. Example: {"summary": {"pattern": "<component>", "replacement": "newcomponent"}}')
    parser_clone.add_argument('--no-link-back', action='store_true', help='Do not link back to the original issue (if not specified, the new issue is linked back to the original one using clonned relation)')
    parser_clone.add_argument('--raw', action='store_true',
                        help='Display raw issue data (JSON)')
    parser_clone.add_argument('--outputformat', dest='output_format',
                        help='Print output in the form given. Use str.format string with {key} or {field["duedate"]} syntax. Use --json to see what keys exist.')

    # move command
    parser_move = subparsers.add_parser('move', help='change a JIRA issue status')
    parser_move.set_defaults(func=cmd_move)
    # so far limiting to a single issue
    parser_move.add_argument('-j', '--id', '--jira_id', metavar='ID', type=str,
                               help='Jira issues ID')
    parser_move.add_argument('--comment', help='Longer comment to be added to the issue')
    parser_move.add_argument('--comment_file', help='Longer comment to be added to issue located in a file')
    parser_move.add_argument('--status', default='Closed', help='Target status (default: Closed)')
    parser_move.add_argument('--resolution', default='Done', help='Resolution of the closure (default: Done)')

    # fields-mapping command
    parser_fields_mapping = subparsers.add_parser('fields-mapping', help='show fields mapping for a project')
    parser_fields_mapping.set_defaults(func=cmd_fields_mapping)
    parser_fields_mapping.add_argument('--project', default='RHEL', help='Which project to show fields for (default RHEL)')
    parser_fields_mapping.add_argument('--issue_type', default='Bug', help='Which issue type do we want to see fields for (default Bug)')
    parser_fields_mapping.add_argument('--only_required', action='store_true', help='Print only required fields')

    if len(sys.argv) <= 1:
        sys.argv.append('--help')

    args = parser.parse_args()
    args.func(args)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
