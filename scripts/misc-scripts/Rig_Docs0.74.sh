#!/bin/bash
# Written by Emilie Hoggarth

# Version 0.74 20201202

if [ -z "$1" ]; then
echo "You must provide a mounted volume location as the 2nd argument"
exit
fi

if [ -z "$2" ]; then
echo "You must provide the project folder on the mediaraid as the 3rd argument"
exit
fi

# Define machine name
machine=$(scutil --get LocalHostName)

while true; do
	echo You are now copying the Rig Docs from "$machine" to $2
    read -p "Are you copying from the rig? (y/n)" yn
   
    case $yn in
        [Yy]* )
		        # Now assuming we have the correct file paths from user, create rig docs folders
				cd $1
				mkdir SS
				mkdir DESKTOP
				mkdir RESOLVE
				
				# Copying the rig docs to the mediaraid
				rsync -rvh /$HOME/Desktop/ $1/DESKTOP
				rsync -rvh /$HOME/Library/Application\ Support/Pomfort/Silverstack[0-9] $1/SS
				rsync -rvh /$HOME/Library/Application\ Support/Pomfort/Livegrade[0-9] $1/SS
				rsync -rvh /$HOME/Documents/drp_batch $1/RESOLVE
				rsync -rvh /Library/Application\ Support/Blackmagic\ Design/DaVinci\ Resolve/LUT $1/RESOLVE
				# TODO work out how to check for psla in SD/docs folders
				break;;
        [Nn]* )
        		break;;
        
        
        * ) 
        		echo "Please answer yes or no (y/n).";;
    esac
done

#Pull all 03_documentation directories
mkdir $1/Rsync_Docs
cd $2
for d in *; do
	echo $d
	rsync -rvh $d/0[0-9]_DOCUMENTATION "$1/Rsync_Docs"/$d/
	done

#move all documentation into one folder for easy offload
cd $1
mkdir "Rig_Docs"
mv $1/RESOLVE $1/Rig_Docs/
mv $1/SS $1/Rig_Docs/
mv $1/DESKTOP $1/Rig_Docs/
mv $1/Rsync_Docs $1/Rig_Docs

# Move rig_docs into the project folder for easy Yoyotta dir naming
mv $1/Rig_Docs $2/