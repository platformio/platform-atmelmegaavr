import sys
import os

from SCons.Script import ARGUMENTS, Import, Return

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

board_fuses = board.get("fuses", {})
if not board_fuses:
    sys.stderr.write("Error: No fuse values specified!\n")
    env.Exit(1)

# Note: the index represents the fuse number
fuses = (
    board_fuses.get("WDTCFG", ""),
    board_fuses.get("BODCFG", ""),
    board_fuses.get("OSCCFG", ""),
    "",  # Reserved
    board_fuses.get("TCD0CFG", ""),
    board_fuses.get("SYSCFG0", ""),
    board_fuses.get("SYSCFG1", ""),
    board_fuses.get("APPEND", ""),
    board_fuses.get("BOOTEND", ""),
)

lock_fuse = board_fuses.get("LOCKBIT", "")

fuses_cmd = [
    "avrdude", "-p", "$BOARD_MCU", "-C",
    '"%s"' % os.path.join(platform.get_package_dir(
        "tool-avrdude-megaavr") or "", "avrdude.conf"),
    "-c", "$UPLOAD_PROTOCOL", "$UPLOAD_FLAGS"
]

if int(ARGUMENTS.get("PIOVERBOSE", 0)):
    fuses_cmd.append("-v")

for idx, value in enumerate(fuses):
    if value:
        fuses_cmd.append("-Ufuse%d:w:%s:m" % (idx, value))

if lock_fuse:
    fuses_cmd.append("-Ulock:w:%s:m" % lock_fuse)

print_fuses_info(fuses, lock_fuse)

fuses_action = env.VerboseAction(" ".join(fuses_cmd), "Setting fuses")

Return("fuses_action")
