from __future__ import annotations

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_RTK_BINARY_NAMES = {"rtk", "rtk.exe"}


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        if self.target_name != "wheel":
            return

        vendor_root = Path(self.root) / "src" / "pbi_agent" / "_vendor" / "rtk"
        has_bundled_rtk = any(
            path.is_file() and path.name in _RTK_BINARY_NAMES
            for path in vendor_root.rglob("*")
        )
        if not has_bundled_rtk:
            return

        build_data["pure_python"] = False
        build_data["infer_tag"] = True
