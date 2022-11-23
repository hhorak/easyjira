#!/bin/env python3

import argparse
import os
import requests
import sys
import codecs # for decoding escapte characters
import urllib
import pprint
import json

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

def print_issues(output_format, issues):
    for issue in issues:
        print(output_format.format(**issue))

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

def cmd_query(args):
    output=[]
    
    # get issues based on ID
    headers = get_headers()
    if args.id:
        for issue in args.id:
            r=requests.get(f"{JIRA_REST_URL}/issue/{issue}", headers=headers)
            output.append(r.json())

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

    print_issues(output_format, output)

def cmd_create(args):
    print("not implemented yet")

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
    print("not implemented yet")
    headers = get_headers()
    query = json.loads(args.json)
    if args.id:
        for issue in args.id:
            print(f'Issue {issue} being updated with: {query}')
            r=requests.put(f"{JIRA_REST_URL}/issue/{issue}", json=query, headers=headers)
            if r.ok:
#            if True:
                print(f'Issue {issue} updated.')
            else:
                print(f'ERROR: Issue {issue} NOT updated.')

def main() -> int:
    """Main program entry that parses args"""

    parser = argparse.ArgumentParser(description='Work with JIRA from cmd-line like with python-bugzilla-cli.')
    subparsers = parser.add_subparsers(help='commands')

    parser_query = subparsers.add_parser('query', help='query JIRA issues')
    parser_query.add_argument('-j', '--id', '--jira_id', metavar='ID', type=str, nargs='+',
                              help='Jira issues ID')
    parser_query.add_argument('--from-url', dest='from_url',
                        help='Use full URL as an argument')
    parser_query.add_argument('--jql', dest='jql',
                        help='Use JQL query')
    parser_query.add_argument('--start_at', dest='start_at', default=0, help='Pagination, start at which item in the output of a single query')
    parser_query.add_argument('--max_results', dest='max_results', default=DEFAULT_MAX_RESULTS, help='Pagination, how many items in the output of a single query, not counting individually requested IDs')

    # the idea here is to use something like print("format from user".format(**issue)) but needs to be validated by some real pythonist for security
    parser_query.add_argument('--outputformat', dest='output_format',
                        help='Print output in the form given. Use str.format string with {key} or {field["duedate"]} syntax. Use --json to see what keys exist.')
    parser_query.set_defaults(func=cmd_query)

    parser_new = subparsers.add_parser('new', help='create a new JIRA issue')
    parser_new.set_defaults(func=cmd_create)

    parser_update = subparsers.add_parser('update', help='update a JIRA issue')
    parser_update.set_defaults(func=cmd_update)
    parser_update.add_argument('-j', '--id', '--jira_id', metavar='ID', type=str, nargs='+',
                               help='Jira issues ID')
    parser_update.add_argument('--json', metavar='json', type=str, required = True,
                               help='JSON that defines what should be changed. See "Updating an Issue via the JIRA REST APIs" section of the Jira API: https://developer.atlassian.com/server/jira/platform/updating-an-issue-via-the-jira-rest-apis-6848604/')

    if len(sys.argv) <= 1:
        sys.argv.append('--help')

    args = parser.parse_args()
    args.func(args)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
