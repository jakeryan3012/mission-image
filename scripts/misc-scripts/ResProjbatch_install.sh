#!/bin/sh

echo $PWD

BASEDIR=$(dirname "$0")
echo "$BASEDIR"

RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/"
RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"

launchctl setenv RESOLVE_SCRIPT_API "$RESOLVE_SCRIPT_API"
launchctl setenv RESOLVE_SCRIPT_LIB "$RESOLVE_SCRIPT_LIB"

cp "$BASEDIR"/ResolveProjBatchExport.py '/Library/Application Support/Blackmagic Design/DaVinci Resolve/Fusion/Scripts/Comp/'