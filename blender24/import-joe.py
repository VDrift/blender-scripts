#!BPY
# -*- coding: iso-8859-1 -*-

"""
Name: 'JOE (.joe)'
Blender: 239
Group: 'Import'
Tooltip: 'Import VDrift JOE file. (.joe)'
"""
######################################################
# JOE Importer
# By: NaN, based on JOE exporter by Joe Venzon
#	  and   MD2 importer by Bob Holcomb
# Date:	24 JAN 10
# Ver:	0.5
######################################################
import Blender
from Blender.Draw import *
from Blender.Window import *
from vdrift import *

#Globals
g_joe_filename = Create("*.joe")
g_image_filename = Create('')

# Events
EVENT_NOEVENT = 1
EVENT_LOAD = 2
EVENT_CHOOSE_FILE = 3
EVENT_CHOOSE_IMAGE = 4
EVENT_EXIT=100

######################################################
# Callbacks
######################################################
def filename_callback(input_filename):
	global g_joe_filename
	g_joe_filename.val = input_filename

def image_callback(input_image):
	global g_image_filename
	g_image_filename.val = input_image
	
def event(evt, val):   
	if (evt == QKEY and not val):
		Blender.Draw.Exit()

def bevent(evt):
	if (evt == EVENT_EXIT):
		Blender.Draw.Exit()
	elif (evt == EVENT_CHOOSE_FILE):
		FileSelector(filename_callback, "JOE File Selection")
	elif (evt == EVENT_CHOOSE_IMAGE):
		FileSelector(image_callback, "Texture Selection")
	elif (evt == EVENT_LOAD):
		if not Blender.sys.exists(g_joe_filename.val):
			PupMenu('Model file does not exist')
		else:
			WaitCursor(1)
			image = load_image(g_image_filename.val)
			joe_file = open(g_joe_filename.val, "rb")
			joe = joe_obj().load(joe_file)
			joe_file.close()
			joe.to_mesh(Blender.sys.basename(g_joe_filename.val), image)
			WaitCursor(0)
			Blender.Redraw()
			Blender.Draw.Exit()

######################################################
# GUI
######################################################
def draw_gui():
	global g_joe_filename, g_image_filename
	Label("JOE Loader", 10, 125, 210, 18)
	BeginAlign()
	g_joe_filename = String("JOE file to load: ", EVENT_NOEVENT, 10, 95, 210, 18, g_joe_filename.val, 255, "JOE file to load")
	Button("Browse", EVENT_CHOOSE_FILE, 220, 95, 80, 18)
	EndAlign()
	BeginAlign()
	g_image_filename = String("Texture file to load: ", EVENT_NOEVENT, 10, 75, 210, 18, g_image_filename.val, 255, "Texture file to load")
	Button("Browse", EVENT_CHOOSE_IMAGE, 220, 75, 80, 18)
	EndAlign()
	Button("Load", EVENT_LOAD, 10, 10, 80, 18)
	Button("Exit", EVENT_EXIT , 140, 10, 80, 18)

if __name__ == '__main__':
	Register(draw_gui, event, bevent) 