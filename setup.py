from distutils.core import setup
from distutils import sysconfig
import py2app
import os
import sys
import subprocess
import shutil
import tempfile
from plistlib import readPlist, writePlist

import vanilla
import defconAppKit
import robofab
import fontTools
import pygments

from drawBotSettings import *

codeSignDeveloperName = None
if "--codesign" in sys.argv:
    try:
        i = sys.argv.index("--codesign")
        codeSignDeveloperName = sys.argv[i+1]
        sys.argv.remove("--codesign")
        sys.argv.remove(codeSignDeveloperName)
    except:
        pass



plist = dict(

	CFBundleDocumentTypes = [
	dict(
		CFBundleTypeExtensions = ["py"],
		CFBundleTypeName = "Python Source File",
		CFBundleTypeRole = "Editor",
		NSDocumentClass = "DrawBotDocument",
	    ),
		
		],
	CFBundleIdentifier = "com.drawbot",
	LSMinimumSystemVersion = "10.6.0",
	CFBundleShortVersionString = version,
	CFBundleVersion = version,
	CFBundleIconFile = "DrawBot.icns",
	NSHumanReadableCopyright = "Copyright by Just van Rossum and Frederik Berlaen.",
    CFBundleURLTypes = [
            dict(
                CFBundleURLName = "com.drawbot",
                CFBundleURLSchemes = [appName.lower()])
        ],
	)


dataFiles = [
        "Resources/English.lproj",
        os.path.dirname(vanilla.__file__),
        ]

for fileName in os.listdir("Resources/Images"):
    baseName, extension = os.path.splitext(fileName)
    if extension.lower() in [".png", ".icns"]:
        fullPath = os.path.join("Resources/Images", fileName)
        dataFiles.append(fullPath)

# build
setup(
    data_files=dataFiles,
    app=[dict(script="DrawBot.py", plist=plist)],
    options = dict(py2app=dict(
                    packages=[
                        os.path.dirname(vanilla.__file__),
                        os.path.dirname(defconAppKit.__file__),
                        os.path.dirname(robofab.__file__),
                        os.path.dirname(pygments.__file__),
                        os.path.dirname(fontTools.__file__),
                        ],
                    )
                )
            )

# fix the icon
path = os.path.join(os.path.dirname(__file__), "dist", "DrawBot.app", "Contents", "Info.plist")
appPlist = readPlist(path)
appPlist["CFBundleIconFile"] = "DrawBot.icns"
writePlist(appPlist, path)

if "-A" not in sys.argv and codeSignDeveloperName:
    # get relevant paths
    distLocation = os.path.join(os.getcwd(), "dist")
    appLocation = os.path.join(distLocation, "%s.app" % appName)
    imgLocation = os.path.join(distLocation,  "img")
    existingDmgLocation = os.path.join(distLocation,  "%s.dmg" % appName)
    dmgLocation = os.path.join(distLocation,  appName)

    # ================
    # = code singing =
    # ================
    print "---------------------"
    print "-   code signing    -"
    cmds = ["codesign", "-f", "-s", "Developer ID Application: %s" % codeSignDeveloperName, appLocation]
    popen = subprocess.Popen(cmds)
    popen.wait()
    print "- done code singing -"
    print "---------------------"


    # ================
    # = creating dmg =
    # ================

    if os.path.exists(existingDmgLocation):
        os.remove(existingDmgLocation)
    
    os.mkdir(imgLocation)
    os.rename(os.path.join(distLocation, "%s.app" %appName), os.path.join(imgLocation, "%s.app" %appName))
    tempDmgName = "%s.tmp.dmg" %appName

    os.system("hdiutil create -srcfolder \"%s\" -volname %s -format UDZO \"%s\"" %(imgLocation, appName, os.path.join(distLocation, tempDmgName)))

    os.system("hdiutil convert -format UDZO -imagekey zlib-level=9 -o \"%s\" \"%s\"" %(dmgLocation, os.path.join(distLocation, tempDmgName)))

    os.remove(os.path.join(distLocation, tempDmgName))

    os.rename(os.path.join(imgLocation, "%s.app" %appName), os.path.join(distLocation, "%s.app" %appName))

    shutil.rmtree(imgLocation)

