#!/bin/env python3

import sys

import easyjira

if __name__ == '__main__':
    ej = easyjira.EasyJira()
    sys.exit(ej.main())
