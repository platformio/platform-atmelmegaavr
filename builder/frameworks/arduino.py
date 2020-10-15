# Copyright 2019-present PlatformIO <contact@platformio.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Arduino

Arduino Wiring-based Framework allows writing cross-platform software to
control devices attached to a wide range of Arduino boards to create all
kinds of creative coding, interactive objects, spaces or physical experiences.

http://arduino.cc/en/Reference/HomePage
"""

import sys
from os.path import isdir, isfile, join

from SCons.Script import DefaultEnvironment

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()
build_core = board.get("build.core", "")

FRAMEWORK_DIR = platform.get_package_dir("framework-arduino-megaavr")
if build_core != "arduino":
    FRAMEWORK_DIR = platform.get_package_dir(
        "framework-arduino-megaavr-%s" % build_core.lower())

assert isdir(FRAMEWORK_DIR)

CPPDEFINES = [
    "ARDUINO_ARCH_MEGAAVR",
    ("ARDUINO", 10808)
]

if "build.usb_product" in board:
    CPPDEFINES += [
        ("USB_VID", board.get("build.hwids")[0][0]),
        ("USB_PID", board.get("build.hwids")[0][1]),
        ("USB_PRODUCT", '\\"%s\\"' %
         board.get("build.usb_product", "").replace('"', "")),
        ("USB_MANUFACTURER", '\\"%s\\"' %
         board.get("vendor", "").replace('"', ""))
    ]

env.SConscript("_bare.py", exports="env")

env.Append(
    CPPDEFINES=CPPDEFINES,

    CPPPATH=[
        join(FRAMEWORK_DIR, "cores", build_core, "api", "deprecated"),
        join(FRAMEWORK_DIR, "cores", build_core)
    ],

    LIBSOURCE_DIRS=[
        join(FRAMEWORK_DIR, "libraries")
    ]
)

if env.subst("$BOARD") in ("nano_every", "uno_wifi_rev2"):
    # Bootloader and fuses for uploading purposes
    bootloader_config = board.get("bootloader", {})
    if "BOOTLOADER_CMD" not in env:
        if env.subst("$BOARD") == "uno_wifi_rev2":
            bootloader_path = join(
                FRAMEWORK_DIR, "bootloaders", board.get("bootloader.file", ""))
            if isfile(bootloader_path):
                env.Replace(BOOTLOADER_CMD='-Uflash:w:"%s":i' % bootloader_path)
            else:
                sys.stderr.write(
                    "Error: Couldn't find bootloader image %s\n" % bootloader_path)
                env.Exit(1)

    if "FUSES_CMD" not in env:
        for fuse in ("OSCCFG", "SYSCFG0", "BOOTEND"):
            if not bootloader_config.get(fuse, ""):
                sys.stderr.write("Error: Missing %s fuse value\n" % fuse)
                env.Exit(1)

        env.Replace(
            FUSES_CMD="-Ufuse2:w:%s:m -Ufuse5:w:%s:m -Ufuse8:w:%s:m" % (
                bootloader_config.get("OSCCFG"),
                bootloader_config.get("SYSCFG0"),
                bootloader_config.get("BOOTEND")
            )
        )

#
# Target: Build Core Library
#

libs = []

if "build.variant" in board:
    variants_dir = join(
        "$PROJECT_DIR", board.get("build.variants_dir")) if board.get(
            "build.variants_dir", "") else join(FRAMEWORK_DIR, "variants")

    env.Append(
        CPPPATH=[
            join(variants_dir, board.get("build.variant"))
        ]
    )
    env.BuildSources(
        join("$BUILD_DIR", "FrameworkArduinoVariant"),
        join(variants_dir, board.get("build.variant"))
    )

env.BuildSources(
    join("$BUILD_DIR", "FrameworkArduino"),
    join(FRAMEWORK_DIR, "cores", build_core)
)

env.Prepend(LIBS=libs)
