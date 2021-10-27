# Atmel AVR Dx: development platform for [PlatformIO](http://platformio.org)

# Usage

1. [Install PlatformIO](http://platformio.org)
2. Create PlatformIO project and configure a platform option in [platformio.ini](http://docs.platformio.org/page/projectconf.html) file:

## Stable version

```ini
[env:stable]
platform = atmelavrdx
board = ...
...
```

## Development version

```ini
[env:development]
platform = https://github.com/brunob45/platform-atmelavrdx.git
board = ...
...
```

# Configuration

Supported boards:
- AVR128DA64
- AVR128DA48
- AVR128DA32
- AVR128DA28

Supported boards with patched toolchain
- AVR32DB28
- AVR32DB32
- AVR32DB48
