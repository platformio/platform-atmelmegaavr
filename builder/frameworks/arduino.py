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

from os.path import isdir, join

from SCons.Script import DefaultEnvironment

from platformio.package.version import pepver_to_semver

env = DefaultEnvironment()
platform = env.PioPlatform()
board = env.BoardConfig()
build_core = board.get("build.core", "")

FRAMEWORK_DIR = platform.get_package_dir("framework-arduino-megaavr")
if build_core != "arduino":
    FRAMEWORK_DIR = platform.get_package_dir(
        "framework-arduino-megaavr-%s" % build_core.lower()
    )

assert isdir(FRAMEWORK_DIR)

CPPDEFINES = ["ARDUINO_ARCH_MEGAAVR", ("ARDUINO", 10808)]

if "build.usb_product" in board:
    CPPDEFINES += [
        ("USB_VID", board.get("build.hwids")[0][0]),
        ("USB_PID", board.get("build.hwids")[0][1]),
        (
            "USB_PRODUCT",
            '\\"%s\\"' % board.get("build.usb_product", "").replace('"', ""),
        ),
        ("USB_MANUFACTURER", '\\"%s\\"' % board.get("vendor", "").replace('"', "")),
    ]

env.SConscript("_bare.py", exports="env")

env.Append(
    CPPDEFINES=CPPDEFINES,
    CPPPATH=[
        join(FRAMEWORK_DIR, "cores", build_core, "api", "deprecated"),
        join(FRAMEWORK_DIR, "cores", build_core),
    ],
    LIBSOURCE_DIRS=[join(FRAMEWORK_DIR, "libraries")],
)

#
# Select oscillator using a special macro
#

oscillator_type = board.get("hardware", {}).get("oscillator", "internal")
if build_core in ("megatinycore", "dxcore"):
    if oscillator_type == "external":
        env.Append(CPPDEFINES=[("CLOCK_SOURCE", 2)])
    elif oscillator_type == "crystal":
        env.Append(CPPDEFINES=[("CLOCK_SOURCE", 1)])
    else:
        env.Append(CPPDEFINES=[("CLOCK_SOURCE", 0)])
elif oscillator_type == "external" and build_core == "MegaCoreX":
    env.Append(CPPDEFINES=["USE_EXTERNAL_OSCILLATOR"])

#
# Additional definitions for DxCore and MegaTinyCore
#

if build_core in ("dxcore", "megatinycore"):
    package_version = pepver_to_semver(platform.get_package_version(
        "framework-arduino-megaavr-%s" % build_core
    ))

    core_macro_name = build_core.upper()
    env.Append(
        CCFLAGS=["-mrelax"],
        CPPDEFINES=[
            (core_macro_name, '\\"%s\\"' % package_version),
            ("%s_MAJOR" % core_macro_name, "%sUL" % package_version.major),
            ("%s_MINOR" % core_macro_name, "%sUL" % package_version.minor),
            ("%s_PATCH" % core_macro_name, "%sUL" % package_version.patch),
            ("%s_RELEASED" % core_macro_name, 1),
            "CORE_ATTACH_ALL",
        ]
    )

    env.Replace(
        CXXFLAGS=[
            "-std=gnu++17",
            "-fpermissive",
            "-fno-exceptions",
            "-fno-threadsafe-statics",
            "-flto",
            "-Wno-sized-deallocation",
            "-Wno-error=narrowing",
        ],
    )

    if build_core == "megatinycore":
        env.Append(
            CPPDEFINES=[
                "TWI_MORS"
            ],
        )
    elif build_core == "dxcore":
        timer = board.get("hardware.millistimer", "B2")
        bootloader = board.get("hardware.uart", "no_bootloader").lower()
        optiboot = "USING_OPTIBOOT" if bootloader != "no_bootloader" else ""

        mvio = ""
        if board.get("hardware.mvio_enable", "no").lower() == "yes":
            if "db" in board.get("build.mcu").lower():
                mvio = "MVIO_ENABLED"
            else:
                pass # MVIO is not supported

        env.Append(
            CPPDEFINES=[
                "TWI_MORS_SINGLE",
                "MILLIS_USE_TIMER" + timer,
                optiboot,
                mvio,
            ],
            LINKFLAGS=[
                "-mrelax",
                "-Wl,--section-start=.FLMAP_SECTION1=%s"
                % board.get("build.arduino.flmap_section1", "0x8000"),
                "-Wl,--section-start=.FLMAP_SECTION2=%s"
                % board.get("build.arduino.flmap_section2", "0x10000"),
                "-Wl,--section-start=.FLMAP_SECTION3=%s"
                % board.get("build.arduino.flmap_section3", "0x18000"),
            ],
        )


#
# Target: Build Core Library
#

libs = []

if "build.variant" in board:
    variants_dir = (
        join("$PROJECT_DIR", board.get("build.variants_dir"))
        if board.get("build.variants_dir", "")
        else join(FRAMEWORK_DIR, "variants")
    )

    env.Append(CPPPATH=[join(variants_dir, board.get("build.variant"))])
    env.BuildSources(
        join("$BUILD_DIR", "FrameworkArduinoVariant"),
        join(variants_dir, board.get("build.variant")),
    )

libs.append(
    env.BuildLibrary(
        join("$BUILD_DIR", "FrameworkArduino"), join(FRAMEWORK_DIR, "cores", build_core)
    )
)

env.Prepend(LIBS=libs)
