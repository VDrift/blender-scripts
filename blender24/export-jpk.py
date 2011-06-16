#!BPY
# -*- coding: iso-8859-1 -*-

"""
Name: 'JPK (.jpk)'
Blender: 239
Group: 'Export'
Tooltip: 'Export VDrift JPK file. (.jpk)'
"""
######################################################
# JPK Exporter
# By: NaN, based on JOE exporter
# Date:	24 JAN 10
# Ver:	0.1
######################################################
import Blender
from Blender.Draw import *
from Blender.Window import *
from vdrift import *

def save_jpk(filename):
	WaitCursor(1)
	jpk = joe_pack().from_mesh()
	jpk.save(filename)
	WaitCursor(0)
	
if __name__ == '__main__':
	FileSelector(save_jpk, "Select JPK")