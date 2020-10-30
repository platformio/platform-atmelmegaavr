import sys
import os

from SCons.Script import ARGUMENTS, COMMAND_LINE_TARGETS, Import, Return

Import("env")


def print_fuses_info(fuses, lock_fuse):
    print("Selected fuses:")
    for idx, value in enumerate(fuses):
        if value:
            print("[fuse%d = %s]" % (idx, value))
    if lock_fuse:
        print("lock = %s" % lock_fuse)


board = env.BoardConfig()
platform = env.PioPlatform()

fuses_section = "fuses"
if "bootloader" in COMMAND_LINE_TARGETS or "UPLOADBOOTCMD" in env:
    fuses_section = "bootloader"

board_fuses = board.get(fuses_section, {})
if not board_fuses and "FUSESFLAGS" not in env:
    sys.stderr.write("Error: No fuse values specified!\n")
    env.Exit(1)

# Note: the index represents the fuse number
fuses = (
    board_fuses.get("wdtcfg", ""),
    board_fuses.get("bodcfg", ""),
    board_fuses.get("osccfg", ""),
    "",  # reserved
    board_fuses.get("tcd0cfg", ""),
    board_fuses.get("syscfg0", ""),
    board_fuses.get("syscfg1", ""),
    board_fuses.get("append", ""),
    board_fuses.get("bootend", ""),
)

lock_fuse = board_fuses.get("LOCKBIT", "")

env.Append(
    FUSESUPLOADER="avrdude",
    FUSESUPLOADERFLAGS=[
        "-p",
        "$BOARD_MCU",
        "-C",
        '"%s"'
        % os.path.join(env.PioPlatform().get_package_dir(
            "tool-avrdude-megaavr") or "", "avrdude.conf"),
    ],
    SETFUSESCMD="$FUSESUPLOADER $FUSESUPLOADERFLAGS $UPLOAD_FLAGS $FUSESFLAGS",
)

env.Append(
    FUSESFLAGS=[
        "-Ufuse%d:w:%s:m" % (idx, value) for idx, value in enumerate(fuses) if value
    ]
)

if lock_fuse:
    env.Append(FUSESFLAGS=["-Ulock:w:%s:m" % lock_fuse])

if int(ARGUMENTS.get("PIOVERBOSE", 0)):
    env.Append(FUSESUPLOADERFLAGS=["-v"])

if not env.BoardConfig().get("upload", {}).get("require_upload_port", False):
    # upload methods via USB
    env.Append(FUSESUPLOADERFLAGS=["-P", "usb"])
else:
    env.AutodetectUploadPort()
    env.Append(FUSESUPLOADERFLAGS=["-P", '"$UPLOAD_PORT"'])

if env.subst("$UPLOAD_PROTOCOL") != "custom":
    env.Append(FUSESUPLOADERFLAGS=["-c", "$UPLOAD_PROTOCOL"])
else:
    print(
        "Warning: The `custom` upload protocol is used! The upload and fuse flags may "
        "conflict!\nMore information: "
        "https://docs.platformio.org/en/latest/platforms/atmelavr.html"
        "#overriding-default-fuses-command\n"
    )

print_fuses_info(fuses, lock_fuse)

fuses_action = env.VerboseAction("$SETFUSESCMD", "Setting fuses")

Return("fuses_action")
