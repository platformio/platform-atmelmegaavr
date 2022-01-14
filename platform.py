# Copyright 2014-present PlatformIO <contact@platformio.org>
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

from platformio.managers.platform import PlatformBase


class AtmelmegaavrPlatform(PlatformBase):

    def configure_default_packages(self, variables, targets):
        if not variables.get("board"):
            return super(AtmelmegaavrPlatform, self).configure_default_packages(
                variables, targets)

        build_core = variables.get(
            "board_build.core", self.board_config(variables.get("board")).get(
                "build.core", "arduino"))

        if "arduino" in variables.get("pioframework", []) and build_core != "arduino":
            framework_package = "framework-arduino-megaavr-%s" % build_core.lower()
            self.frameworks["arduino"]["package"] = framework_package
            self.packages[framework_package]["optional"] = False
            self.packages["framework-arduino-megaavr"]["optional"] = True

            if build_core in ("MegaCoreX", "megatinycore", "dxcore"):
                self.packages["toolchain-atmelavr"]["version"] = "~2.70300.0"
                self.packages["tool-avrdude-megaavr"]["version"] = "~2.60300.0"

        if any(t in targets for t in ("fuses", "bootloader")):
            self.packages["tool-avrdude-megaavr"]["optional"] = False

        return super(AtmelmegaavrPlatform, self).configure_default_packages(
            variables, targets)
