#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Elena
"""

import os
from shutil import copyfile


for i in range(1, 41):
    dir_name = str(i)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    copyfile('input.py', dir_name + '/input.py')
    copyfile('lib2.lib', dir_name + '/lib2.lib')
