import sys
import os

from SCons.Script import ARGUMENTS, COMMAND_LINE_TARGETS, Import, Return

Import("env")


def get_wdtcfg_fuse():
    return 0x00


def is_dxcore_dd_target():
    return core == "dxcore" and "dd" in board.get("build.mcu").lower()


def get_dxcore_bodcfg_fuse(bod, bodmode):
    bod = bod.lower()
    bodmode = bodmode.lower()

    bodlev_bits = {
        "1.9v": 0b000,
        "1v9": 0b000,
        "2.45v": 0b001,
        "2v45": 0b001,
        "2.7v": 0b010,
        "2.70v": 0b010,
        "2v7": 0b010,
        "2v70": 0b010,
        "2.85v": 0b011,
        "2v85": 0b011,
    }

    bodmode_bits = {
        "disabled": None,
        "enabled": 0b00101,
        "ensampfast": 0b00110,
        "ensampslow": 0b10110,
        "samplefast": 0b01010,
        "sampledfast": 0b01010,
        "sampleslow": 0b11010,
        "sampledslow": 0b11010,
        "sampdisfast": 0b01000,
        "sampdisslow": 0b11000,
        "endisholdwake": 0b01100,
    }

    if bodmode not in bodmode_bits:
        sys.stderr.write("Error: Unsupported DxCore BOD mode '%s' for %s\n" % (bodmode, target))
        env.Exit(1)

    if bodmode_bits[bodmode] is None:
        return 0x00

    if bod not in bodlev_bits:
        sys.stderr.write("Error: Unsupported DxCore BOD level '%s' for %s\n" % (bod, target))
        env.Exit(1)

    return (bodlev_bits[bod] << 5) | bodmode_bits[bodmode]


def get_bodcfg_fuse(bod, bodmode="disabled"):
    if core == "dxcore":
        return get_dxcore_bodcfg_fuse(bod, bodmode)
    elif core in ("MegaCoreX", "megatinycore"):
        if bod == "4.3v":
            return 0xF4
        elif bod == "2.6v":
            return 0x54
        elif bod == "1.8v":
            return 0x14
        else:  # bod disabled
            return 0x00


def get_osccfg_fuse(f_cpu, oscillator):
    if core == "dxcore":
        return 0x00
    elif (
        f_cpu == "20000000L" or f_cpu == "10000000L" or f_cpu == "5000000L"
    ) and oscillator == "internal":
        return 0x02
    else:
        return 0x01


def get_tcd0cfg_fuse():
    if core == "dxcore":
        # DxCore's own bootloader/fuse flows do not write TCD0CFG.
        return None
    return 0x00


def get_syscfg0_fuse(eesave, pin, uart):
    eesave_bit = 1 if eesave == "yes" else 0
    if is_dxcore_dd_target():
        if pin == "gpio" and uart == "no_bootloader":
            resetpin_bits = 0b01
        else:
            # PlatformIO currently exposes only reset/gpio, so map these to the
            # safe AVR-DD defaults: RESET+UPDI when reset is selected or a
            # bootloader is in use.
            resetpin_bits = 0b11
        return 0xC0 | (resetpin_bits << 3) | eesave_bit
    if core in ("MegaCoreX", "dxcore"):
        if pin == "gpio":
            if uart == "no_bootloader":
                rstpin_bit = 0
            else:
                rstpin_bit = 1
        else:
            rstpin_bit = 1
        return 0xC0 | rstpin_bit << 3 | eesave_bit

    elif core == "megatinycore":
        if pin == "gpio":
            updipin_bits = 0
        elif pin == "updi":
            updipin_bits = 1
        else:
            updipin_bits = 2
        return 0xC0 | updipin_bits << 2 | eesave_bit

    sys.stderr.write("Error: Couldn't calculate SYSCFG0  fuse for %s\n" % target)
    env.Exit(1)


# Handle AVR-DB's differently since these has MVIO pins
def get_syscfg1_fuse(mvio):
    if is_dxcore_dd_target():
        startuptime = str(board.get("hardware.startuptime", "8")).lower().replace("ms", "")
        sut_bits = {
            "0": 0b000,
            "1": 0b001,
            "2": 0b010,
            "4": 0b011,
            "8": 0b100,
            "16": 0b101,
            "32": 0b110,
            "64": 0b111,
        }.get(startuptime, 0b100)
        mvio_bits = 0b01 if mvio == "yes" else 0b10
        return (mvio_bits << 3) | sut_bits
    if core == "dxcore" and ("db" in board.get("build.mcu").lower()):
        if(mvio == "yes"):
            return 0x0E
        else:
            return 0x16
    else:
        return 0x06

    sys.stderr.write("Error: Couldn't calculate SYSCFG1  fuse for %s\n" % target)
    env.Exit(1)


# Called CODESIZE on AVR-Dx
def get_append_fuse():
    return 0x00


# Called BOOTSIZE on AVR-Dx
def get_bootend_fuse(uart):
    if uart == "no_bootloader":
        return 0x00
    else:
        if core in ("MegaCoreX", "megatinycore"):
            return 0x02
        elif core == "dxcore":
            return 0x01

    sys.stderr.write("Error: Couldn't calculate bootend for %s\n" % target)
    env.Exit(1)


def get_lockbit_fuse():
    if core in ("arduino", "MegaCoreX", "megatinycore"):
        return 0xC5
    elif core == "dxcore":
        # DxCore's bootloader/fuse flows do not write lockbits by default.
        return None
    else:
        sys.stderr.write("Error: Couldn't calculate lockbit for %s\n" % target)
        env.Exit(1)


def print_fuses_info(fuse_values, fuse_names, lock_fuse):
    if "upload" in COMMAND_LINE_TARGETS:
        return
    print("\nSelected fuses:")
    print("-------------------------")
    for idx, value in enumerate(fuse_values):
        if value:
            print("[fuse%d / %-8s = %s]" % (idx, fuse_names[idx].lower(), value))
    if lock_fuse:
        print("[lock  / lockbit  = %s]" % lock_fuse)
    print("-------------------------\n")


def format_fuse_value(value):
    if value is None:
        return ""
    return "0x%.2X" % value


def calculate_fuses(board_config, predefined_fuses):
    f_cpu = board_config.get("build.f_cpu", "16000000L").upper()
    oscillator = board_config.get("hardware.oscillator", "internal").lower()
    bod = board_config.get("hardware.bod", "2.6v").lower()
    bodmode = board_config.get("hardware.bodmode", "disabled").lower()
    uart = board_config.get("hardware.uart", "no_bootloader").lower()
    eesave = board_config.get("hardware.eesave", "yes").lower()
    mvio = board_config.get("hardware.mvio_enable", "no").lower()
    if core in ("MegaCoreX", "dxcore"):
        pin = board_config.get("hardware.rstpin", "reset").lower()
        # Guard that prevents the user from turning the reset pin
        # into a GPIO while using a bootloader
        if uart != "no_bootloader":
            pin = "reset"
    elif core == "megatinycore":
        pin = board_config.get("hardware.updipin", "updi").lower()

    print("\nTARGET CONFIGURATION:")
    print("-------------------------")
    print("Target = %s" % target)
    print("Clock speed = %s" % f_cpu)
    print("Oscillator = %s" % oscillator)
    print("BOD level = %s" % bod)
    if core == "dxcore":
        print("BOD mode = %s" % bodmode)
    print("Save EEPROM = %s" % eesave)
    if core == "dxcore" and "db" in board.get("build.mcu").lower():
        print("MVIO enable = %s" % mvio)
    print("%s = %s" % (
        "Reset pin mode" if core in ("MegaCoreX", "dxcore") else "UPDI pin mode", pin))
    print("-------------------------")

    return (
        predefined_fuses[0] or format_fuse_value(get_wdtcfg_fuse()),
        predefined_fuses[1] or format_fuse_value(get_bodcfg_fuse(bod, bodmode)),
        predefined_fuses[2] or format_fuse_value(get_osccfg_fuse(f_cpu, oscillator)),
        "",  # reserved
        predefined_fuses[4] or format_fuse_value(get_tcd0cfg_fuse()),
        predefined_fuses[5] or format_fuse_value(get_syscfg0_fuse(eesave, pin, uart)),
        predefined_fuses[6] or format_fuse_value(get_syscfg1_fuse(mvio)),
        predefined_fuses[7] or format_fuse_value(get_append_fuse()),
        predefined_fuses[8] or format_fuse_value(get_bootend_fuse(uart)),
    )


board = env.BoardConfig()
platform = env.PioPlatform()
core = board.get("build.core", "")

target = (
    board.get("build.mcu").lower()
    if board.get("build.mcu", "")
    else env.subst("$BOARD").lower()
)

fuses_section = "fuses"
if "bootloader" in COMMAND_LINE_TARGETS or "UPLOADBOOTCMD" in env:
    fuses_section = "bootloader"

# Note: the index represents the fuse number
fuse_names = (
    "wdtcfg",
    "bodcfg",
    "osccfg",
    "",  # reserved
    "tcd0cfg",
    "syscfg0",
    "syscfg1",
    "append" if core in ("MegaCoreX", "megatinycore") else "codesize",
    "bootend" if core in ("MegaCoreX", "megatinycore") else "bootsize"
)

board_fuses = board.get(fuses_section, {})
if (
    not board_fuses
    and "FUSESFLAGS" not in env
    and core not in ("MegaCoreX", "megatinycore", "dxcore")
):
    sys.stderr.write(
        "Error: Dynamic fuses generation for %s / %s is not supported. "
        "Please specify fuses in platformio.ini\n" % (core, env.subst("$BOARD"))
    )
    env.Exit(1)

fuse_values = [board_fuses.get(fname, "") for fname in fuse_names]
lock_fuse = board_fuses.get("lockbit", format_fuse_value(get_lockbit_fuse()))
if core in ("MegaCoreX", "megatinycore", "dxcore"):
    fuse_values = calculate_fuses(board, fuse_values)


env.Append(
    FUSESUPLOADER="avrdude",
    FUSESUPLOADERFLAGS=[
        "-p",
        "$BOARD_MCU",
        "-C",
        os.path.join(
            env.PioPlatform().get_package_dir(
                "tool-avrdude" if core in ("MegaCoreX", "megatinycore", "dxcore") else "tool-avrdude-megaavr"
            )
            or "",
            "avrdude.conf",
        ),
    ],
    SETFUSESCMD="$FUSESUPLOADER $FUSESUPLOADERFLAGS $UPLOAD_FLAGS $FUSESFLAGS",
)

env.Append(
    FUSESFLAGS=[
        "-Ufuse%d:w:%s:m" % (idx, value)
        for idx, value in enumerate(fuse_values)
        if value
    ]
)

if lock_fuse:
    env.Append(FUSESFLAGS=["-Ulock:w:%s:m" % lock_fuse])

if int(ARGUMENTS.get("PIOVERBOSE", 0)):
    env.Append(FUSESUPLOADERFLAGS=["-v"])

# Add upload serial port to Avrdude flags list if a jtag2updi programmer
if env.subst("$UPLOAD_PROTOCOL") in ("jtag2updi", "serialupdi"):
    env.AutodetectUploadPort()
    env.Append(FUSESUPLOADERFLAGS=["-P", '"$UPLOAD_PORT"'])
else:
    # upload methods via USB
    env.Append(FUSESUPLOADERFLAGS=["-P", "usb"])


if env.subst("$UPLOAD_PROTOCOL") != "custom":
    env.Append(FUSESUPLOADERFLAGS=["-c", "$UPLOAD_PROTOCOL"])
else:
    print(
        "Warning: The `custom` upload protocol is used! The upload and fuse flags may "
        "conflict!\nMore information: "
        "https://docs.platformio.org/en/latest/platforms/atmelavr.html"
        "#overriding-default-fuses-command\n"
    )

print_fuses_info(fuse_values, fuse_names, lock_fuse)

fuses_action = env.VerboseAction("$SETFUSESCMD", "Setting fuses...")

Return("fuses_action")
