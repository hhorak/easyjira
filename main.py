#!/bin/env python3

import sys

import easyjira

if __name__ == '__main__':
    rj = easyjira.EasyJira()
    sys.exit(rj.main())
