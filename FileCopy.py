#!/usr/bin/env python
##required for mac testing (UNIX OS) to execute the correct version/interpreter of python for our shell command


import glob, os, shutil 
#import modules required to run script
#glob is used to find matching pathnames in this case the "*.txt" files then matching back to the unix shell and then fetching the contents of the file and changing the directories with the OS module.
# shutil (shell utility) is used to iterate over your rule, in the case of this code copy the file over to a new directory recursively  


src = "/Users/jamiefaria/Documents/";
dst = "/Users/jamiefaria/Documents/Python_test/";
# setting the source (src) and destination (dst) directories


files = glob.iglob(os.path.join(src, "*.txt")) 
#what files I want to move/copy then finds all pathways under the source directory matching the text file type


for file in files:
    if os.path.isfile(file):
        shutil.copy2(file, dst)
#and if the pathway matched the file type then it will copy it to the destination
#could also replace copy2 with move if you dont want duplicates
#copy2 is used to preserve more metadata (ie permissions) whereas copy() just copies the txt file with limited metadata.
