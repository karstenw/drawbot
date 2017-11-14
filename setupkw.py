from distutils.core import setup
from distutils import sysconfig
import py2app
import os
import sys
import subprocess
import shutil
import tempfile
import datetime
from plistlib import readPlist, writePlist

import vanilla
import defconAppKit
# import robofab
import fontTools
import pygments

from drawBot.drawBotSettings import __version__, appName

rawTimeStamp = datetime.datetime.today()
timeStamp = rawTimeStamp.strftime("%y%m%d%H%M")


def getValueFromSysArgv(key, default=None):
    if key in sys.argv:
        try:
            i = sys.argv.index(key)
            value = sys.argv[i + 1]
            sys.argv.remove(key)
            sys.argv.remove(value)
            return value
        except Exception:
            pass
    return default


osxMinVersion = "10.6.8"

plist = dict(

    CFBundleDocumentTypes=[
        dict(
            CFBundleTypeExtensions=["py"],
            CFBundleTypeName="Python Source File",
            CFBundleTypeRole="Editor",
            CFBundleTypeIconFile="pythonIcon.icns",
            NSDocumentClass="DrawBotDocument",
        ),
    ],
    CFBundleIdentifier="com.drawbot",
    LSMinimumSystemVersion=osxMinVersion,
    LSApplicationCategoryType="public.app-category.graphics-design",
    CFBundleShortVersionString=__version__,
    CFBundleVersion=__version__,
    CFBundleIconFile="DrawBot.icns",
    NSHumanReadableCopyright="Copyright by Just van Rossum and Frederik Berlaen.",
    CFBundleURLTypes=[
        dict(
            CFBundleURLName="com.drawbot",
            CFBundleURLSchemes=[appName.lower()])
    ],
)


dataFiles = [
    "Resources/English.lproj",
    "drawBot/context/tools/gifsicle",
    "drawBot/context/tools/mkbitmap",
    "drawBot/context/tools/potrace"
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
    options={
        'py2app': {
            'iconfile': "Resources/English.lproj/DrawBot.icns",
#             'packages': [
#                 'vanilla',
#                 'defcon',
#                 'defconAppKit',
#                 # 'robofab',
#                 'fontParts',
#                 'mutatorMath',
#                 'woffTools',
#                 'compositor',
#                 'feaTools2',
#                 'ufo2svg',
#                 'booleanOperations',
#                 #'pyclipper',
#                 'pygments',
#                 'jedi',
#                 'fontTools',
#                 # 'xml'
#             ],
            "excludes": ["TkInter", "babel", "sphinx", "docutils"],
        }
    }
)

