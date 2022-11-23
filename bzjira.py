#!/bin/env python3

import argparse
import os
import requests
import sys

JIRA_PROJECTS_URL = "https://issues.redhat.com"
JIRA_REST_URL = f"{JIRA_PROJECTS_URL}/rest/api/2"

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

def cmd_query(args):
    output=[]
    
    # get issues based on ID
    for issue in args.id:
        headers = get_headers()
        r=requests.get(f"{JIRA_REST_URL}/issue/{issue}", headers=headers, verify=False)
        output.append(r.json())

    # get issues based on url with a query
    #r=requests.post(f"{REST_URL}/search", json=args.from_url, headers=headers, verify=False)
    #output.append(r.json())

    # get issues based on jql only
    r=requests.post(f"{REST_URL}/search", json=args.jql, headers=headers, verify=False)
    output.append(r.json()['issues'])

    output_format = args.output_format if args.output_format else DEFAULT_OUTPUT
    print_issues(output_format, output)

def cmd_create(args):
    print("not implemented yet")

def cmd_update(args):
    """
    query={"update":{"labels":[{"add":"jira-bugzilla-resync"}]}}
    r=requests.put(f"{REST_URL}/issue/RHELPLAN-95816", json=query, headers=headers, verify=False)
    """
    print("not implemented yet")

def main() -> int:
    """Main program entry that parses args"""

    parser = argparse.ArgumentParser(description='Work with jira from cmd-line like with python-bugzilla-cli.')
    subparsers = parser.add_subparsers(help='commands')

    parser_query = subparsers.add_parser('query', help='query JIRA issues')
    parser_query.add_argument('-j', '--id', '--jira_id', metavar='ID', type=str, nargs='+',
                              help='Jira issues ID')
    parser_query.add_argument('--from-url', dest='from_url',
                        help='Use full URL as an argument')
    parser_query.add_argument('--jql', dest='jql',
                        help='Use JQL query')

    # the idea here is to use something like print("format from user".format(**issue)) but needs to be validated by some real pythonist for security
    parser_query.add_argument('--outputformat', dest='output_format',
                        help='Print output in the form given. Use str.format string with {key} or {field["duedate"]} syntax. Use --json to see what keys exist.')
    parser_query.set_defaults(func=cmd_query)

    parser_new = subparsers.add_parser('new', help='create a new JIRA issue')


    if len(sys.argv) <= 1:
        sys.argv.append('--help')

    args = parser.parse_args()
    args.func(args)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
