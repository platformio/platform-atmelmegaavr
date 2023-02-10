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
import re

from SCons.Script import Import, Return

Import("env")

board = env.BoardConfig()
platform = env.PioPlatform()
core = board.get("build.core", "")


def get_suitable_optiboot_binary(framework_dir, board_config):
    uart = board_config.get("hardware.uart", "no_bootloader").lower()
    if uart == "no_bootloader":
        return ""

    if core == "MegaCoreX":
        if not uart.endswith(("_alt", "_def")):
            uart = uart + "_def"

        bootloader_led = board_config.get("bootloader.led_pin", "A7").upper()
        bootloader_speed = board_config.get("bootloader.speed", env.subst("$UPLOAD_SPEED"))
        bootloader_file = "Optiboot_mega0_%s_%s_%s.hex" % (
            uart.upper(), bootloader_speed, bootloader_led)

        bootloader_path = os.path.join(
            framework_dir, "bootloaders", "optiboot", "bootloaders", "mega0",
            bootloader_speed, bootloader_file
        )
    else:  # dxcore
        mcu_size = re.match(r'avr(\d+)', board.get("build.mcu")).group(1)
        uart = uart.lower().replace("uart", "ser")
        bootloader_file = "optiboot_dx%s_%s.hex" % (mcu_size, uart)
        bootloader_path = os.path.join(
            framework_dir, "bootloaders", "hex", bootloader_file
        )

    print('Using bootloader', bootloader_file)

    return bootloader_path


framework_dir = ""
if env.get("PIOFRAMEWORK", []):
    framework_dir = platform.get_package_dir(platform.frameworks[env.get(
        "PIOFRAMEWORK")[0]]["package"])

#
# Bootloader processing
#

bootloader_path = board.get("bootloader.file", "")
if core in ["MegaCoreX", "dxcore"]:
    if not os.path.isfile(bootloader_path):
        if board.get("hardware.uart", "no_bootloader").lower() == "no_bootloader":
            sys.stderr.write("Error: `no bootloader` selected in board config!\n")
            env.Exit(1)
        bootloader_path = get_suitable_optiboot_binary(framework_dir, board)
else:
    if not os.path.isfile(bootloader_path):
        bootloader_path = os.path.join(framework_dir, "bootloaders", bootloader_path)

    if not board.get("bootloader", {}):
        sys.stderr.write("Error: missing bootloader configuration!\n")
        env.Exit(1)

if not os.path.isfile(bootloader_path):
    bootloader_path = os.path.join(framework_dir, "bootloaders", bootloader_path)

if not os.path.isfile(bootloader_path) and "BOOTFLAGS" not in env:
    sys.stderr.write("Error: Couldn't find bootloader image %s\n" % bootloader_path)
    env.Exit(1)

env.Append(
    BOOTUPLOADER="avrdude",
    BOOTUPLOADERFLAGS=[
        "-p",
        "$BOARD_MCU",
        "-C",
        os.path.join(
            env.PioPlatform().get_package_dir(
                "tool-avrdude" if core in ("MegaCoreX", "megatinycore") else "tool-avrdude-megaavr"
            )
            or "",
            "avrdude.conf",
        ),
    ],
    BOOTFLAGS=["-U", "flash:w:%s:i" % bootloader_path],
    UPLOADBOOTCMD="$BOOTUPLOADER $BOOTUPLOADERFLAGS $UPLOAD_FLAGS $BOOTFLAGS",
)

if not env.BoardConfig().get("upload", {}).get("require_upload_port", False):
    # upload methods via USB
    env.Append(BOOTUPLOADERFLAGS=["-P", "usb"])
else:
    env.AutodetectUploadPort()
    env.Append(FUSESUPLOADERFLAGS=["-P", '"$UPLOAD_PORT"'])

if env.subst("$UPLOAD_PROTOCOL") != "custom":
    env.Append(BOOTUPLOADERFLAGS=["-c", "$UPLOAD_PROTOCOL"])
else:
    print(
        "Warning: The `custom` upload protocol is used! The upload and fuse flags may "
        "conflict!\nMore information: "
        "https://docs.platformio.org/en/latest/platforms/atmelavr.html"
        "#overriding-default-bootloader-command\n"
    )

fuses_action = env.SConscript("fuses.py", exports="env")

bootloader_actions = [
    fuses_action,
    env.VerboseAction("$UPLOADBOOTCMD", "Uploading bootloader"),
]

Return("bootloader_actions")
