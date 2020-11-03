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

#
# Default flags for bare-metal programming (without any framework layers)
#

from SCons.Script import Import

Import("env")

env.Append(
    ASFLAGS=["-x", "assembler-with-cpp"],

    CFLAGS=[
        "-std=gnu11",
        "-fno-fat-lto-objects"
    ],

    CCFLAGS=[
        "-Os",
        "-w",
        "-ffunction-sections",
        "-fdata-sections",
        "-flto",
        "-mmcu=$BOARD_MCU"
    ],

    CPPDEFINES=[
        ("F_CPU", "$BOARD_F_CPU")
    ],

    CXXFLAGS=[
        "-std=gnu++11",
        "-fno-exceptions",
        "-fno-threadsafe-statics",
        "-fpermissive",
        "-Wno-error=narrowing"
    ],

    LINKFLAGS=[
        "-Os",
        "-flto",
        "-mmcu=$BOARD_MCU",
        "-Wl,--gc-sections",
        "-Wl,--section-start=.text=%s" % ("0x200"
        if env.BoardConfig().get("hardware.uart", "no_bootloader") != "no_bootloader"
        else env.BoardConfig().get("build.text_section_start", "0x0")),
        "-fuse-linker-plugin"
    ],

    LIBS=["m"]
)

# copy CCFLAGS to ASFLAGS (-x assembler-with-cpp mode)
env.Append(ASFLAGS=env.get("CCFLAGS", [])[:])
