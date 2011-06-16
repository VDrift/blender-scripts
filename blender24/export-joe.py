#!BPY
# -*- coding: iso-8859-1 -*-

"""
Name: 'JOE (.joe)'
Blender: 239
Group: 'Export'
Tooltip: 'Export VDrift JOE file. (.joe)'
"""
######################################################
# JOE Exporter
# By: NaN, based on JOE importer
# Date:	24 JAN 10
# Ver:	0.1
######################################################
import sys
sys.path.append(".")
import Blender
from Blender.Draw import *
from Blender.Window import *
from vdrift import *

g_mesh_obj = None

def save_joe(filename):
	WaitCursor(1)
	joe = joe_obj().from_mesh(g_mesh_obj)
	mesh = g_mesh_obj.getData(mesh=True)
	if 'joename' in mesh.properties:
		filename = mesh.properties['joename']
	joe_file = open(filename, "wb")
	joe.save(joe_file)
	joe_file.close()
	WaitCursor(0)
	
if __name__ == '__main__':
	obs = Blender.Object.GetSelected()
	if len(obs) == 0 or obs[0].getType() != 'Mesh' or len(obs[0].getData().faces) == 0:
		PupMenu('Please select a Mesh')
	else:
		g_mesh_obj = obs[0]
		FileSelector(save_joe, "Select JOE")
