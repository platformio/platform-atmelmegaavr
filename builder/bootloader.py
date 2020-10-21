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

import sys
import os

from SCons.Script import ARGUMENTS, Import, Return

Import("env")

board = env.BoardConfig()
platform = env.PioPlatform()
core = board.get("build.core", "")

AVRDUDE_PATH = platform.get_package_dir("tool-avrdude-megaavr") or ""

common_cmd = [
    "avrdude", "-p", "$BOARD_MCU", "-e", "-C",
    '"%s"' % os.path.join(AVRDUDE_PATH, "avrdude.conf"),
    "-c", "$UPLOAD_PROTOCOL", "$UPLOAD_FLAGS"
]

framework_dir = ""
if env.get("PIOFRAMEWORK", []):
    framework_dir = platform.get_package_dir(platform.frameworks[env.get(
        "PIOFRAMEWORK")[0]]["package"])

#
# Bootloader processing
#

bootloader_path = board.get("bootloader.file", "")
if not os.path.isfile(bootloader_path):
    bootloader_path = os.path.join(framework_dir, "bootloaders", bootloader_path)

if not os.path.isfile(bootloader_path):
    sys.stderr.write("Error: Couldn't find bootloader image\n")
    env.Exit(1)

bootloader_flags = ['-Uflash:w:"%s":i' % bootloader_path]

#
# Fuses processing
#

bootloader_fuses = board.get("bootloader", {})
if not bootloader_fuses:
    sys.stderr.write("Error: missing bootloader configuration!\n")
    env.Exit(1)

bootloader_fuses = board.get("bootloader", {})
if not bootloader_fuses:
    sys.stderr.write("Error: No fuse values specified!\n")
    env.Exit(1)

# Note: the index represents the fuse number
fuses = (
    bootloader_fuses.get("WDTCFG", ""),
    bootloader_fuses.get("BODCFG", ""),
    bootloader_fuses.get("OSCCFG", ""),
    "",  # Reserved
    bootloader_fuses.get("TCD0CFG", ""),
    bootloader_fuses.get("SYSCFG0", ""),
    bootloader_fuses.get("SYSCFG1", ""),
    bootloader_fuses.get("APPEND", ""),
    bootloader_fuses.get("BOOTEND", ""),
)

lock_fuse = bootloader_fuses.get("LOCKBIT", "")

fuses_cmd = [
    "avrdude", "-p", "$BOARD_MCU", "-C",
    '"%s"' % os.path.join(AVRDUDE_PATH, "avrdude.conf"),
    "-c", "$UPLOAD_PROTOCOL", "$UPLOAD_FLAGS"
]

if int(ARGUMENTS.get("PIOVERBOSE", 0)):
    fuses_cmd.append("-v")

for idx, value in enumerate(fuses):
    if value:
        fuses_cmd.append("-Ufuse%d:w:%s:m" % (idx, value))

if lock_fuse:
    fuses_cmd.append("-Ulock:w:%s:m" % lock_fuse)

fuses_action = env.VerboseAction(" ".join(fuses_cmd), "Setting fuses")

bootloader_actions = [
    fuses_action,
    env.VerboseAction(" ".join(common_cmd + bootloader_flags), "Uploading bootloader")
]

Return("bootloader_actions")
