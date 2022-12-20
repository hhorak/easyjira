#!/bin/env python3

import os
import sys
import pytest
import json
import shlex
from unittest.mock import patch

currentdir = os.path.dirname(os.path.realpath(__file__))
parentdir = os.path.dirname(currentdir)
sys.path.append(parentdir)

import easyjira


def _read_doc_file(filename):
    with open(filename) as f:
        return '\n'.join(f.readlines())


# easy state machine where after each keyword, we find text between two separators (----)
def _parse_doc_file(filename):
    with open(filename) as f:
        content = f.readlines()
    #content = _read_doc_file(filename)
    state = None
    what = None
    output = {}
    for line in content:
        #print(line)
        if '// test_case usage' in line:
            what = 'usage'
        if '// test_case rest api call' in line:
            what = 'restapi'
        elif line.startswith('----'):
            if state:
                state = None
                what = None
            else:
                state = 'accepts'
            print("New state:" + str(state))
        else:
            if state == 'accepts' and what:
                if what in output:
                    output[what].append(line)
                else:
                    output[what] = [line]
    return output


def test_help(capsys):
    rj = easyjira.EasyJira()
    with pytest.raises(SystemExit):
        rj.main()
    captured = capsys.readouterr()
    print(captured.out)
    assert 'Work with JIRA from cmd-line' in captured.out
            

def test_query(capsys):
    rj = easyjira.EasyJira()
    with pytest.raises(SystemExit):
        rj.main(fake_args=['--simulate', 'query', '-j', 'RHELPLAN-142726'])
    captured = capsys.readouterr()
    assert 'requests.get("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-142726"' in captured.err
    assert 'params = None' in captured.err


def test_query2(capsys):
    rj = easyjira.EasyJira()
    with pytest.raises(SystemExit):
        rj.main(fake_args=['--simulate', 'query', '--jql', 'reporter = currentUser() order by created DESC'])
    captured = capsys.readouterr()
    assert 'requests.get("https://issues.redhat.com/rest/api/2/search"' in captured.err
    assert 'params = "jql=reporter+%3D+currentUser' in captured.err


def test_move(capsys):
    rj = easyjira.EasyJira()
    with pytest.raises(SystemExit):
        rj.main(fake_args=['--simulate', 'move', '--status', 'Closed', '--resolution', 'Done', '--comment', 'closing', '-j', 'RHELPLAN-138763'])
    captured = capsys.readouterr()
    assert 'requests.get("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-138763/transitions' in captured.err
    assert 'params = None' in captured.err
    assert "json = \"{'transition': {'id': '221'}, 'fields': {'resolution': {'name': 'Done'}}}\"" in captured.err
    assert 'response = requests.post("https://issues.redhat.com/rest/api/2/issue/RHELPLAN-138763/transitions", json=json' in captured.err


def test_doc_query(capsys):
    input_data = _parse_doc_file(parentdir + '/docs/query.adoc')
    command_args = ['--simulate'] + shlex.split(input_data['usage'][0])[1:]
    rj = easyjira.EasyJira()
    with pytest.raises(SystemExit):
        rj.main(fake_args=command_args)
    captured = capsys.readouterr()
    for expected in input_data['restapi']:
        assert expected in captured.err
    #assert 'params = None' in captured.err


if __name__ == '__main__':
    # this is here for debugging purposes to see how adoc is parsed
    # normally this file is run by 'pytest' command
    print(_parse_doc_file(parentdir + '/docs/query.adoc'))
