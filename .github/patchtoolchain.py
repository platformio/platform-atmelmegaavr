#!/usr/bin/env python3

import os
import re
import json
import sys

from shutil import copyfile
from pathlib import Path
from six.moves.urllib import request
from zipfile import ZipFile
from bs4 import BeautifulSoup

isverbose = "-v" in sys.argv or "--verbose" in sys.argv
def print_verbose(*args):
    if isverbose:
        print(" ".join(map(str, args)))


def find_file(dir, match):
    # function to find all files in a directory tree
    result = []
    for e in os.listdir(str(dir)):
        fullpath = dir / e
        if fullpath.is_file() and re.search(match, str(fullpath.as_posix())):
            result += [fullpath]
        elif fullpath.is_dir():
            result += find_file(fullpath, match)
    return result


# find platformio installation path
if "USERPROFILE" in os.environ:  # windows
    PlatformioPath = Path(os.environ["USERPROFILE"]) / ".platformio"
elif "HOME" in os.environ:  # linux
    PlatformioPath = Path(os.environ["HOME"]) / ".platformio"
else:
    PlatformioPath = Path(os.curdir)

if not PlatformioPath.exists():
    print("Cannot find Platformio at", PlatformioPath)
    exit(1)
else:
    print("Found Platformio at", PlatformioPath)


# find atmelavr toolchain
ToolchainPath = PlatformioPath / "packages/toolchain-atmelavr"
if not ToolchainPath.exists():
    print("Cannot find atmelavr toolchain at", ToolchainPath)
    exit(2)
else:
    print("Found toolchain at", ToolchainPath)


# get pack list from atmel's website
print("Retrieving packs informaton...")
downloadlink = "http://packs.download.atmel.com/"
htmltext = request.urlopen(downloadlink).read().decode("utf-8")
soup = BeautifulSoup(htmltext, "html.parser")
# find latest pack version
link = next(button.get("data-link") for button in soup.find_all("button")
            if button.get("data-link") and "AVR-Dx" in button.get("data-link"))


# get latest pack file from atmel's website
AvrDaToolkitPack = Path(link)
if not AvrDaToolkitPack.exists():
    print("Downloading", AvrDaToolkitPack)
    downloadlink += str(AvrDaToolkitPack)
    request.urlretrieve(downloadlink, str(AvrDaToolkitPack))
else:
    print("Using local", AvrDaToolkitPack)

AvrDaToolkitPack = Path(link)
AvrDaToolkitPath = Path(AvrDaToolkitPack.stem)


# extract pack file
if not AvrDaToolkitPath.exists():
    print("Extracting ", AvrDaToolkitPack, "into", AvrDaToolkitPath)
    ZipFile(str(AvrDaToolkitPack), "r").extractall(str(AvrDaToolkitPath))

print_verbose("Copying files...")


# filter to gather only the files we want
filefilter = str(AvrDaToolkitPath) + \
    r"/(gcc|include)/.*(/specs-.*|\d+\.[aoh]$)"

# find all header, linker and specs files needed for compilation
for f in find_file(AvrDaToolkitPath, filefilter):
    if re.search(r".*\.h$", str(f)):  # is header file
        mynewdir = ToolchainPath / "avr/include/avr"
    elif re.search(r".*\.[ao]$", str(f)):  # is linker file
        mynewdir = ToolchainPath / "avr/lib" / str(f).split(os.sep)[-2]
    else:  # is specs file
        mynewdir = ToolchainPath / "lib/gcc/avr/"
        mynewdir /= os.listdir(str(mynewdir))[0]
        mynewdir /= "device-specs"

    # copy file
    copyfile(str(f), str(mynewdir / f.name))

    # remove administrator rights from file
    os.chmod(str(mynewdir / f.name), 420)  # 644 in octal

    print_verbose(f, "->", mynewdir)

print("Success!")
