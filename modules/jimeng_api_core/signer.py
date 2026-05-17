"""
Signature helpers for Jimeng API requests.

This module keeps request signatures, cookie shape, and common query params
aligned with the newer public jimeng-api chain to reduce 3018 permission errors.
"""

import hashlib
import random
import time
import uuid
from typing import Any, Dict


# Core request constants synced from actively maintained chain
PLATFORM_CODE = "7"
VERSION_CODE = "8.4.0"
DA_VERSION = "3.3.8"
WEB_VERSION = "7.5.0"
AIGC_FEATURES = "app_lip_sync"
DEFAULT_AID = 513695


class JimengSigner:
    """Generate request signatures, headers, and params."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        # Keep web/device identities stable for one client instance.
        self._web_id = self.generate_web_id()
        self._uid = uuid.uuid4().hex

        if debug:
            print("Signer initialized")

    def _get_md5(self, uri: str, device_time: int) -> str:
        """Generate MD5 signature from the request URI and timestamp."""
        path = uri[-7:] if len(uri) >= 7 else uri
        sign_string = f"9e2c|{path}|{PLATFORM_CODE}|{VERSION_CODE}|{device_time}||11ac"

        if self.debug:
            print(f"Sign string: {sign_string}")

        sign = hashlib.md5(sign_string.encode("utf-8")).hexdigest()

        if self.debug:
            print(f"Sign: {sign}")

        return sign

    def _build_cookie(self, session_id: str, device_time: int) -> str:
        """Build cookie fields expected by the current web request flow."""
        return "; ".join(
            [
                f"_tea_web_id={self._web_id}",
                "is_staff_user=false",
                "store-region=cn-gd",
                "store-region-src=uid",
                f"sid_guard={session_id}%7C{device_time}%7C5184000%7CMon%2C+03-Feb-2025+08%3A17%3A09+GMT",
                f"uid_tt={self._uid}",
                f"uid_tt_ss={self._uid}",
                f"sid_tt={session_id}",
                f"sessionid={session_id}",
                f"sessionid_ss={session_id}",
            ]
        )

    def generate_device_time(self) -> int:
        """Generate request timestamp (seconds)."""
        device_time = int(time.time())
        if self.debug:
            print(f"Device time: {device_time}")
        return device_time

    def generate_uuid(self) -> str:
        """Generate UUID string."""
        generated_uuid = str(uuid.uuid4())
        if self.debug:
            print(f"UUID: {generated_uuid}")
        return generated_uuid

    def generate_web_id(self) -> int:
        """Generate pseudo Web ID."""
        web_id = int(random.random() * 999999999999999999 + 7000000000000000000)
        if self.debug:
            print(f"Web ID: {web_id}")
        return web_id

    def get_headers(self, uri: str, session_id: str) -> Dict[str, str]:
        """Build headers for a Jimeng request."""
        device_time = self.generate_device_time()
        sign = self._get_md5(uri, device_time)
        cookie = self._build_cookie(session_id, device_time)

        headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-language": "zh-CN,zh;q=0.9",
            "Cache-control": "no-cache",
            "Appvr": VERSION_CODE,
            "Pf": PLATFORM_CODE,
            "Origin": "https://jimeng.jianying.com",
            "Pragma": "no-cache",
            "Priority": "u=1, i",
            "Referer": "https://jimeng.jianying.com/",
            "Sec-Ch-Ua": '"Google Chrome";v="142", "Chromium";v="142", "Not_A Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "Cookie": cookie,
            "Device-Time": str(device_time),
            "Sign": sign,
            "Sign-Ver": "1",
        }

        if self.debug:
            print("Headers generated")
            for key, value in headers.items():
                if key in {"Cookie", "Sign"}:
                    continue
                print(f"  {key}: {value}")
            print("  Cookie: [HIDDEN]")
            print(f"  Sign: {sign}")

        return headers

    def get_request_params(self) -> Dict[str, Any]:
        """Build query parameters for a Jimeng request."""
        params = {
            "aid": DEFAULT_AID,
            "device_platform": "web",
            "region": "CN",
            "webId": self._web_id,
            "da_version": DA_VERSION,
            "os": "windows",
            "web_component_open_flag": 1,
            "web_version": WEB_VERSION,
            "aigc_features": AIGC_FEATURES,
        }

        if self.debug:
            print("Params generated:")
            for key, value in params.items():
                print(f"  {key}: {value}")

        return params
