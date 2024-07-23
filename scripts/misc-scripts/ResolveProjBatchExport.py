# Written by Emilie Hoggarth 2020
# With thanks to Alex Golding

#version 0.3

import sys
import os
user=os.environ.get('USER')

if sys.platform.startswith("darwin"):
	sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Examples")
	sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
	projDbPath = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Resolve Disk Database/Resolve Projects/Users/guest/Projects"
	if not os.path.isdir(projDbPath):
		print("{} does not exist trying ~{}".format(projDbPath, projDbPath))
		projDbPath = os.path.expanduser('~' + projDbPath)
		print(projDbPath)
		if not os.path.isdir(projDbPath):
			print("Unable to find project databases")
	logFile = "/Library/Application Support/Blackmagic Design/DaVinci Resolve/logs/ResolveProjBatchExport.log"
else:
	print("Platform not yet supported")

# Unused from resolve api readme
SOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/"
RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"

# make a drp folder on the desktop
saveLoc = os.path.expanduser("~/Documents/drp_batch/")
folderChecker = os.path.isdir(saveLoc)
if folderChecker == False:
	os.mkdir(saveLoc)

# Saves out each project as a drp to the desktop
from python_get_resolve import GetResolve
resolve = app.GetResolve()
pm = resolve.GetProjectManager()
proj = pm.GetProjectsInCurrentFolder()
for i in proj.values(): pm.ExportProject(i, saveLoc + i)