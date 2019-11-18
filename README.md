# Atmel megaAVR: development platform for [PlatformIO](http://platformio.org)
[![Build Status](https://travis-ci.org/platformio/platform-atmelmegaavr.svg?branch=develop)](https://travis-ci.org/platformio/platform-atmelmegaavr)
[![Build status](https://ci.appveyor.com/api/projects/status/wm6hx8n8c23dfbnk/branch/develop?svg=true)](https://ci.appveyor.com/project/ivankravets/platform-atmelmegaavr/branch/develop)

Microchip's megaAVR is suitable for applications requiring large amounts of code and offers substantial program and data memories with performance up to 20 MIPS. Based on industry-leading, proven technology, the megaAVR family offers Microchip's widest selection of devices in terms of memories, pin counts, and peripherals.

* [Home](http://platformio.org/platforms/atmelmegaavr) (home page in PlatformIO Platform Registry)
* [Documentation](http://docs.platformio.org/page/platforms/atmelmegaavr.html) (advanced usage, packages, boards, frameworks, etc.)

# Usage

1. [Install PlatformIO](http://platformio.org)
2. Create PlatformIO project and configure a platform option in [platformio.ini](http://docs.platformio.org/page/projectconf.html) file:

## Stable version

```ini
[env:stable]
platform = atmelmegaavr
board = ...
...
```

## Development version

```ini
[env:development]
platform = https://github.com/platformio/platform-atmelmegaavr.git
board = ...
...
```

# Configuration

Please navigate to [documentation](http://docs.platformio.org/page/platforms/atmelmegaavr.html).
