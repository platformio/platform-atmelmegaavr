#!/usr/bin/env python3

import os
import re
import json
import sys

from shutil import copyfile
from pathlib import Path
from urllib import request
import xml.etree.ElementTree as ET
from zipfile import ZipFile

isverbose = "-v" in sys.argv or "--verbose" in sys.argv


def print_verbose(*args):
    if isverbose:
        print(" ".join(map(str, args)))


def find_file(dir: Path, match):
    # function to find all files in a directory tree
    result = []
    for e in os.listdir(dir):
        fullpath = dir / e
        if fullpath.is_file() and re.search(match, str(fullpath)):
            result += [fullpath]
        elif fullpath.is_dir():
            result += find_file(fullpath, match)
    return result


# load template for board definition
boardtemplate = json.loads("""
{
    "build": {
      "extra_flags": "",
      "f_cpu": "4000000UL",
      "mcu": "avr128da48"
    },
    "frameworks": [],
    "platforms": ["atmelavrdx"],
    "name": "avr128da48",
    "upload": {
      "maximum_ram_size": 16384,
      "maximum_size": 131072,
      "protocol": "custom",
      "command": "pymcuprog erase && pymcuprog write -f $SOURCE"
    },
    "url": "https://www.microchip.com/wwwproducts/en/avr128da48",
    "vendor": "Microchip"
  }
""")

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

# find atmelavrdx package
if (PlatformioPath / "platforms/atmelavrdx").exists():
    PlatformPath = PlatformioPath / "platforms/atmelavrdx"
elif (PlatformioPath / "platforms/atmelmegaavr").exists():
    PlatformPath = PlatformioPath / "platforms/atmelmegaavr"
else:
    print("Cannot find atmelavrdx platform")
    exit(2)

print("Found atmelavrdx at", PlatformPath)

os.chdir(ToolchainPath)

# get pack list from atmel's website
print("Retrieving packs information...")
repo = 'http://packs.download.atmel.com/'
index_url = repo + 'index.idx'
with  request.urlopen(index_url) as response:
    index = response.read()
index_root = ET.fromstring(index)


ns = { 'atmel': 'http://packs.download.atmel.com/pack-idx-atmel-extension' }
avrdx = index_root.find('./pdsc[@atmel:name = "AVR-Dx_DFP"]', ns)
version = avrdx.get('version')
url = avrdx.get('url')
devices = [device.get('name') for device in avrdx.findall('./atmel:releases/atmel:release[1]/atmel:devices/atmel:device', ns)]

link = 'Atmel.AVR-Dx_DFP.' + version + '.atpack'

AvrDaToolkitPack = Path(link)
if not AvrDaToolkitPack.exists():
    print("Downloading", AvrDaToolkitPack, repo + link)
    request.urlretrieve(repo + link, AvrDaToolkitPack)
else:
    print("Using local", AvrDaToolkitPack)

AvrDaToolkitPack = Path(link)
AvrDaToolkitPath = Path(AvrDaToolkitPack.stem)

if not AvrDaToolkitPath.exists():
    print("Extracting ", AvrDaToolkitPack, "into", AvrDaToolkitPath)
    ZipFile(AvrDaToolkitPack, "r").extractall(AvrDaToolkitPath)

print_verbose("Copying files...")

filefilter = str(AvrDaToolkitPath) + \
    r"/(gcc|include)/.*(/specs-.*|\d+\.[aoh]$)"

if not (PlatformPath / "boards").exists():
    (PlatformPath / "boards").mkdir()

# find all header, linker and specs files needed for compilation
for f in find_file(AvrDaToolkitPath, filefilter):
    if re.search(r".*\.h$", str(f)):  # is header file
        mynewdir = ToolchainPath / "avr/include/avr"
    elif re.search(r".*\.[ao]$", str(f)):  # is linker file
        mynewdir = ToolchainPath / "avr/lib" / str(f).split(os.sep)[-2]
    else:  # is specs file
        mynewdir = ToolchainPath / "lib/gcc/avr/"
        mynewdir /= os.listdir(mynewdir)[0]
        mynewdir /= "device-specs"

    # copy file
    copyfile(f, mynewdir / f.name)

    # remove administrator rights from file
    os.chmod(mynewdir / f.name, 420)  # 644 in octal

    print_verbose(f, "->", mynewdir)

    boardinfo = re.match(r"^io(avr(\d+)d(\w)(\d+))$", f.stem)
    if boardinfo is not None:
        # create board definition file
        boardtemplate["build"]["mcu"] = boardinfo.group(1)
        boardtemplate["name"] = boardinfo.group(1).upper()
        boardtemplate["upload"]["maximum_ram_size"] = int(
            boardinfo.group(2)) * 128
        boardtemplate["upload"]["maximum_size"] = int(
            boardinfo.group(2)) * 1024
        boardtemplate["url"] = re.sub(
            r"/avr\d+d[ab]\d+$", "/"+boardinfo.group(1), boardtemplate["url"])

        newboardfile = PlatformPath / "boards" / (boardinfo.group(1).upper()+".json")
        print(newboardfile)
        json.dump(boardtemplate, open(newboardfile, "w+"), indent=4)

        print_verbose("Board definition file created ->", newboardfile)

print("Success!")
