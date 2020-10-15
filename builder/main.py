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

from os.path import join

from SCons.Script import (ARGUMENTS, COMMAND_LINE_TARGETS, AlwaysBuild,
                          Builder, Default, DefaultEnvironment)

from platformio.util import get_serial_ports


def BeforeUpload(target, source, env):  # pylint: disable=W0613,W0621
    upload_options = {}
    if "BOARD" in env:
        upload_options = env.BoardConfig().get("upload", {})

    if env.subst("$UPLOAD_SPEED"):
        env.Append(UPLOADERFLAGS=["-b", "$UPLOAD_SPEED"])

    # extra upload flags
    if "extra_flags" in upload_options:
        env.Append(UPLOADERFLAGS=upload_options.get("extra_flags"))

    if upload_options and not upload_options.get("require_upload_port", False):
        # upload methods via USB
        if env.subst("$UPLOAD_PROTOCOL") in (
            "xplainedmini_updi",
            "xplainedpro_updi",
            "curiosity_updi",
            "jtagice3_updi",
        ):
            env.Append(UPLOADERFLAGS=["-P", "usb"])
        return

    env.AutodetectUploadPort()
    env.Append(UPLOADERFLAGS=["-P", '"$UPLOAD_PORT"'])

    before_ports = get_serial_ports()

    if upload_options.get("use_1200bps_touch", False):
        env.TouchSerialPort("$UPLOAD_PORT", 1200)

    if upload_options.get("wait_for_upload_port", False):
        env.Replace(UPLOAD_PORT=env.WaitForNewSerialPort(before_ports))


env = DefaultEnvironment()
env.SConscript("compat.py", exports="env")

env.Replace(
    AR="avr-gcc-ar",
    AS="avr-as",
    CC="avr-gcc",
    GDB="avr-gdb",
    CXX="avr-g++",
    OBJCOPY="avr-objcopy",
    RANLIB="avr-gcc-ranlib",
    SIZETOOL="avr-size",

    ARFLAGS=["rc"],

    SIZEPROGREGEXP=r"^(?:\.text|\.data|\.rodata|\.bootloader)\s+([0-9]+).*",
    SIZEDATAREGEXP=r"^(?:\.data|\.bss|\.noinit)\s+([0-9]+).* ",
    SIZEEEPROMREGEXP=r"^(?:\.eeprom)\s+([0-9]+).*",
    SIZECHECKCMD="$SIZETOOL -A -d $SOURCES",
    SIZEPRINTCMD='$SIZETOOL --mcu=$BOARD_MCU -C -d $SOURCES',

    UPLOADER="avrdude",
    UPLOADERFLAGS=[
        "-p", "$BOARD_MCU", "-C",
        '"%s"' % join(env.PioPlatform().get_package_dir(
            "tool-avrdude-megaavr") or "", "avrdude.conf"),
        "-c", "$UPLOAD_PROTOCOL", "-D", "-V"
    ],

    PROGSUFFIX=".elf"
)

env.Append(
    BUILDERS=dict(
        ElfToBin=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "binary",
                "-R",
                ".eeprom",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".bin"
        ),

        ElfToEep=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "ihex",
                "-j",
                ".eeprom",
                '--set-section-flags=.eeprom="alloc,load"',
                "--no-change-warnings",
                "--change-section-lma",
                ".eeprom=0",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".eep"
        ),

        ElfToHex=Builder(
            action=env.VerboseAction(" ".join([
                "$OBJCOPY",
                "-O",
                "ihex",
                "-R",
                ".eeprom",
                "$SOURCES",
                "$TARGET"
            ]), "Building $TARGET"),
            suffix=".hex"
        )
    )
)

# Allow user to override via pre:script
if env.get("PROGNAME", "program") == "program":
    env.Replace(PROGNAME="firmware")

if not env.get("PIOFRAMEWORK"):
    env.SConscript("frameworks/_bare.py", exports="env")

#
# Target: Build executable and linkable firmware
#

target_elf = None
if "nobuild" in COMMAND_LINE_TARGETS:
    target_elf = join("$BUILD_DIR", "${PROGNAME}.elf")
    target_firm = join("$BUILD_DIR", "${PROGNAME}.hex")
else:
    target_elf = env.BuildProgram()
    target_firm = env.ElfToHex(join("$BUILD_DIR", "${PROGNAME}"), target_elf)

AlwaysBuild(env.Alias("nobuild", target_firm))
target_buildprog = env.Alias("buildprog", target_firm, target_firm)

#
# Target: Print binary size
#

target_size = env.AddPlatformTarget(
    "size",
    target_elf,
    env.VerboseAction("$SIZEPRINTCMD", "Calculating size $SOURCE"),
    "Program Size",
    "Calculate program size",
)

#
# Target: Upload by default .hex file
#

upload_protocol = env.subst("$UPLOAD_PROTOCOL")

if upload_protocol == "custom":
    upload_actions = [env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")]
else:
    upload_actions = [
        env.VerboseAction(BeforeUpload, "Looking for upload port..."),
        env.VerboseAction("$UPLOADCMD", "Uploading $SOURCE")
    ]

if int(ARGUMENTS.get("PIOVERBOSE", 0)):
    env.Prepend(UPLOADERFLAGS=["-v"])

upload_cmd = ["-U", "flash:w:$SOURCES:i"]

if "FUSES_CMD" in env:
    upload_cmd.append(env.get("FUSES_CMD"))

if "BOOTLOADER_CMD" in env:
    upload_cmd.append(env.get("BOOTLOADER_CMD"))

env.Replace(
    UPLOADCMD='$UPLOADER $UPLOADERFLAGS %s' % " ".join(upload_cmd))

env.AddPlatformTarget("upload", target_firm, upload_actions, "Upload")

#
# Target: Upload firmware using external programmer
#

env.AddPlatformTarget(
    "program",
    target_firm,
    env.VerboseAction("$UPLOADCMD", "Programming $SOURCE"),
    "Upload using Programmer",
)

#
# Setup default targets
#

Default([target_buildprog, target_size])
