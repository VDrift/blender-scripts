#!BPY
# -*- coding: iso-8859-1 -*-

"""
Name: 'JPK (.jpk)'
Blender: 239
Group: 'Import'
Tooltip: 'Import VDrift JPK file. (.jpk)'
"""
######################################################
# JPK Importer
# By: NaN, based on JOE importer
# Date:	24 JAN 10
# Ver:	0.4
######################################################
import sys
sys.path.append(".")

import Blender
from Blender.Draw import *
from Blender.Window import *
from vdrift import *

def load_jpk(filename):
	WaitCursor(1)
	jpk = joe_pack().load(filename)
	jpk.to_mesh()
	WaitCursor(0)
	
if __name__ == '__main__':
	FileSelector(load_jpk, "Select JPK")
