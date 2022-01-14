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
    for e in os.listdir(str(dir)):
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
    "core": "dxcore",
    "extra_flags": "-DARDUINO_AVR_AVR128DA48 -DARDUINO_avrda -DMILLIS_USE_TIMERB0",
    "f_cpu": "24000000L",
    "mcu": "avr128da48",
    "variant": "48pin-standard"
  },
  "hardware": {
    "oscillator": "internal"
  },
  "frameworks": [
    "arduino"
  ],
  "name": "AVR128DA48",
  "upload": {
    "maximum_ram_size": 16384,
    "maximum_size": 131072,
    "protocol": "jtag2updi",
    "speed": 115200
  },
  "url": "https://www.microchip.com/wwwproducts/en/AVR128DA48",
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

os.chdir(str(ToolchainPath))

# get pack list from atmel's website
print("Retrieving packs information...")
repo = 'http://packs.download.atmel.com/'
with request.urlopen(repo + 'index.idx') as response:
    index = response.read()
index_root = ET.fromstring(index)


ns = {'atmel': 'http://packs.download.atmel.com/pack-idx-atmel-extension'}
avrdx = index_root.find('./pdsc[@atmel:name = "AVR-Dx_DFP"]', ns)
version = avrdx.get('version')
url = avrdx.get('url')
devices = [device.get('name') for device in avrdx.findall(
    './atmel:releases/atmel:release[1]/atmel:devices/atmel:device', ns)]

link = 'Atmel.AVR-Dx_DFP.' + version + '.atpack'

# get latest pack file from atmel's website
AvrDaToolkitPack = Path(link)
if not AvrDaToolkitPack.exists():
    print("Downloading", AvrDaToolkitPack, repo + link)
    request.urlretrieve(repo + link, str(AvrDaToolkitPack))
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
        mynewdir /= os.listdir(str(mynewdir))[0]
        mynewdir /= "device-specs"

    # copy file
    copyfile(str(f), str(mynewdir / f.name))

    # remove administrator rights from file
    os.chmod(str(mynewdir / f.name), 420)  # 644 in octal

    print_verbose(f, "->", mynewdir)

    # group(1): avr128da48
    # group(2): 128
    # group(3): a
    # group(4): 48
    boardinfo = re.match(r"^io(avr(\d+)d(\w)(\d+))$", f.stem)
    if boardinfo is not None:
        # create board definition file
        boardtemplate["build"]["extra_flags"] = "-DARDUINO_AVR_{0} -DARDUINO_avrd{1} -DMILLIS_USE_TIMERB0".format(
            boardinfo.group(1).upper(),
            boardinfo.group(3))
        boardtemplate["build"]["mcu"] = boardinfo.group(1)
        boardtemplate["build"]["variant"] = "{0}pin-standard".format(
            boardinfo.group(4))
        boardtemplate["name"] = boardinfo.group(1).upper()
        boardtemplate["upload"]["maximum_ram_size"] = int(
            boardinfo.group(2)) * 128
        boardtemplate["upload"]["maximum_size"] = int(
            boardinfo.group(2)) * 1024
        boardtemplate["url"] = "https://www.microchip.com/wwwproducts/en/{0}".format(
            boardinfo.group(1).upper())

        newboardfile = PlatformPath / "boards" / \
            (boardinfo.group(1).upper()+".json")
        print(newboardfile)

        with open(str(newboardfile), "w+") as fd:
            fd.write(json.dumps(boardtemplate, indent=2) + '\n')

        print_verbose("Board definition file created ->", newboardfile)

print("Success!")
