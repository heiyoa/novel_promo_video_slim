#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鍗虫ⅵ鐢熷浘妯″潡锛堢畝鍖栫増宸ヤ綔娴侊級

鍔熻兘锛?1. 浣跨敤鍗虫ⅵ閫嗗悜API鐢熸垚鎸囧畾鍙傛暟鐨勫簳鍥?
2. 鏀寔鑷畾涔夋彁绀鸿瘝銆佸浘鐗囨瘮渚嬨€佹ā鍨嬬増鏈?
3. 鑷姩涓嬭浇骞朵繚瀛樼敓鎴愮殑鍥剧墖
"""

import sys
import os
import time
import json
import subprocess
import uuid
from pathlib import Path
from typing import Optional

# Windows缂栫爜瑙勮寖 - 寮哄埗UTF-8杈撳嚭
sys.stdout.reconfigure(encoding='utf-8')

# 瀵煎叆鍗虫ⅵAPI鍖?
from jimeng_api_core import (
    JimengClient,
    ModelVersion,
    AspectRatio,
    Resolution,
    JimengAPIException,
    JimengAuthException,
    JimengContentFilterException,
    JimengInsufficientPointsException,
    JimengGenerateException
)


CHECK_SCRIPT_PATH = Path(
    r"C:\Users\Administrator\.codex\skills\jimeng-reverse-api\scripts\check_jimeng_upstream.py"
)
UPSTREAM_REPO = "zhizinan1997/jimeng-free-api-all"


def _find_workspace_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "Projects").exists():
            return candidate
    return start.parent


def _find_local_upstream_dir(workspace_root: Path) -> Optional[Path]:
    projects_dir = workspace_root / "Projects"
    if not projects_dir.exists():
        return None

    for candidate in projects_dir.glob("**/jimeng-free-api-all-main/package.json"):
        return candidate.parent

    for candidate in projects_dir.rglob("package.json"):
        parent = candidate.parent
        if "jimeng-free-api-all" in parent.name.lower():
            return parent
    return None


def _is_session_related_error(message: str) -> bool:
    text = (message or "").lower()
    hints = (
        "session",
        "sessionid",
        "cookie",
        "auth",
        "token",
        "unauthorized",
        "forbidden",
        "expired",
        "401",
        "403",
        "login",
    )
    return any(hint in text for hint in hints)


def _prompt_for_new_session() -> None:
    print("[ACTION] Current sessionid looks invalid/expired. Please provide a new sessionid and rerun.")


def _run_upstream_check() -> None:
    if not CHECK_SCRIPT_PATH.exists():
        print(f"[WARN] Upstream checker not found: {CHECK_SCRIPT_PATH}")
        return

    workspace_root = _find_workspace_root(Path(__file__).resolve())
    output_path = workspace_root / "fanqie_outputs" / "jimeng_upstream_check.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(CHECK_SCRIPT_PATH),
        "--repo",
        UPSTREAM_REPO,
        "--output",
        str(output_path),
    ]
    local_dir = _find_local_upstream_dir(workspace_root)
    if local_dir:
        cmd.extend(["--local-dir", str(local_dir)])

    result = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        print(f"[WARN] Failed to check upstream updates: {detail}")
        return

    print(f"[INFO] Upstream version check written to: {output_path}")
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        upstream = payload.get("upstream", {}) if isinstance(payload, dict) else {}
        tag = upstream.get("latest_release_tag") or "unknown"
        url = upstream.get("latest_release_url") or ""
        print(f"[INFO] Latest upstream release: {tag}")
        if url:
            print(f"[INFO] Release URL: {url}")
    except Exception:
        pass


def _parse_enum(enum_cls, value, default):
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    key = str(value).strip()
    if not key:
        return default
    if key in enum_cls.__members__:
        return enum_cls[key]
    for item in enum_cls:
        if item.value == key:
            return item
    return default


class JimengImageGenerator:
    """鍗虫ⅵ鐢熷浘鐢熸垚鍣ㄧ被"""
    
    def __init__(
        self,
        session_id: str,
        output_dir: str = "./outputs/images",
        model=ModelVersion.JIMENG_4_5,
        ratio=AspectRatio.RATIO_9_16,
        resolution=Resolution.RESOLUTION_2K,
        debug: bool = True,
        timeout_sec: int = 45,
        verify_tls: bool = False,
    ):
        """
        鍒濆鍖栧嵆姊︾敓鍥剧敓鎴愬櫒
        
        Args:
            session_id: 鍗虫ⅵAPI鐨剆essionid
            output_dir: 鍥剧墖淇濆瓨鐩綍
            model: 妯″瀷鐗堟湰锛岄粯璁ゅ嵆姊?.5
            ratio: 鍥剧墖姣斾緥锛岄粯璁?:16
            resolution: 鍥剧墖鍒嗚鲸鐜囷紝榛樿2K
            debug: 鏄惁鍚敤璋冭瘯妯″紡
        """
        self.session_id = session_id
        self.output_dir = Path(output_dir)
        self.model = _parse_enum(ModelVersion, model, ModelVersion.JIMENG_4_5)
        self.ratio = _parse_enum(AspectRatio, ratio, AspectRatio.RATIO_9_16)
        self.resolution = _parse_enum(Resolution, resolution, Resolution.RESOLUTION_2K)
        self.debug = debug
        self.timeout_sec = timeout_sec
        self.verify_tls = verify_tls
        
        # 鍒涘缓杈撳嚭鐩綍
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 鍒濆鍖栧嵆姊﹀鎴风
        self.client = JimengClient(
            session_id=session_id,
            model=self.model,
            ratio=self.ratio,
            resolution=self.resolution,
            timeout=self.timeout_sec,
            debug=debug,
        )

    def _to_image_input_list(self, image_inputs) -> list[str]:
        if image_inputs is None:
            return []
        if isinstance(image_inputs, (str, Path)):
            value = str(image_inputs).strip()
            return [value] if value else []
        result = []
        for item in image_inputs:
            value = str(item or "").strip()
            if value:
                result.append(value)
        return result

    def _read_image_input_bytes(self, image_input: str) -> tuple[bytes, str]:
        import requests

        raw = str(image_input or "").strip()
        if not raw:
            raise JimengGenerateException("Image input cannot be empty")

        verify_tls = bool(getattr(self, "verify_tls", False))
        if raw.startswith("http://") or raw.startswith("https://"):
            response = requests.get(raw, timeout=60, verify=verify_tls)
            response.raise_for_status()
            file_name = Path(raw.split("?", 1)[0]).name or f"{uuid.uuid4().hex}.jpg"
            return response.content, file_name

        path = Path(raw)
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_file():
            raise JimengGenerateException(f"Image file not found: {path}")
        return path.read_bytes(), path.name

    def _upload_image_for_composition(self, image_input: str) -> str:
        import requests

        image_bytes, file_name = self._read_image_input_bytes(image_input)
        proof_data = {
            "scene": "aigc_image",
            "file_name": file_name or f"{uuid.uuid4().hex}.jpg",
            "file_size": len(image_bytes),
        }
        proof_result = self.client._call_api("/mweb/v1/get_upload_image_proof", proof_data)
        proof_info = proof_result.get("proof_info") if isinstance(proof_result, dict) else None
        if not isinstance(proof_info, dict):
            raise JimengGenerateException(f"Invalid upload proof: {proof_result}")

        query_params = proof_info.get("query_params")
        headers = proof_info.get("headers")
        image_uri = proof_info.get("image_uri")
        if not query_params or not headers or not image_uri:
            raise JimengGenerateException(f"Incomplete upload proof: {proof_info}")

        verify_tls = bool(getattr(self, "verify_tls", False))
        upload_resp = requests.post(
            "https://imagex.bytedanceapi.com/",
            params=query_params,
            headers=headers,
            files={"file": (file_name, image_bytes, "image/jpeg")},
            timeout=self.timeout_sec,
            verify=verify_tls,
        )
        if not upload_resp.ok:
            raise JimengGenerateException(
                f"Image upload failed: {upload_resp.status_code} {upload_resp.text[:300]}"
            )
        return str(image_uri)

    def _build_composition_request(
        self,
        prompt: str,
        image_uris: list[str],
        negative_prompt: str = "",
    ) -> dict:
        signer = self.client.signer
        component_id = signer.generate_uuid()
        submit_id = signer.generate_uuid()
        resolution_type = self.resolution.value
        sample_strength = float(getattr(self.client, "sample_strength", 0.5))

        scene_option = {
            "type": "image",
            "scene": "ImageBasicGenerate",
            "modelReqKey": self.model.value,
            "resolutionType": resolution_type,
            "abilityList": [
                {
                    "abilityName": "byte_edit",
                    "strength": sample_strength,
                    "source": {"imageUrl": f"blob:https://jimeng.jianying.com/{signer.generate_uuid()}"},
                }
                for _ in image_uris
            ],
            "reportParams": {
                "enterSource": "generate",
                "vipSource": "generate",
                "extraVipFunctionKey": f"{self.model.value}-{resolution_type}",
                "useVipFunctionDetailsReporterHoc": True,
            },
        }
        prompt_with_refs = "#" * (len(image_uris) * 2) + prompt

        return {
            "extend": {"root_model": self.model.model_code},
            "submit_id": submit_id,
            "metrics_extra": json.dumps(
                {
                    "promptSource": "custom",
                    "generateCount": 1,
                    "enterFrom": "click",
                    "sceneOptions": json.dumps([scene_option], ensure_ascii=False),
                    "generateId": submit_id,
                    "isRegenerate": False,
                },
                ensure_ascii=False,
            ),
            "draft_content": json.dumps(
                {
                    "type": "draft",
                    "id": signer.generate_uuid(),
                    "min_version": "3.2.9",
                    "min_features": [],
                    "is_from_tsn": True,
                    "version": "3.2.9",
                    "main_component_id": component_id,
                    "component_list": [
                        {
                            "type": "image_base_component",
                            "id": component_id,
                            "min_version": "3.0.2",
                            "aigc_mode": "workbench",
                            "metadata": {
                                "type": "",
                                "id": signer.generate_uuid(),
                                "created_platform": 3,
                                "created_platform_version": "",
                                "created_time_in_ms": str(int(time.time() * 1000)),
                                "created_did": "",
                            },
                            "generate_type": "blend",
                            "abilities": {
                                "type": "",
                                "id": signer.generate_uuid(),
                                "blend": {
                                    "type": "",
                                    "id": signer.generate_uuid(),
                                    "min_version": "3.2.9",
                                    "min_features": [],
                                    "core_param": {
                                        "type": "",
                                        "id": signer.generate_uuid(),
                                        "model": self.model.model_code,
                                        "prompt": prompt_with_refs,
                                        "negative_prompt": negative_prompt,
                                        "sample_strength": sample_strength,
                                        "image_ratio": self.client.image_ratio,
                                        "large_image_info": {
                                            "type": "",
                                            "id": signer.generate_uuid(),
                                            "height": self.client.height,
                                            "width": self.client.width,
                                            "resolution_type": resolution_type,
                                        },
                                        "intelligent_ratio": False,
                                    },
                                    "ability_list": [
                                        {
                                            "type": "",
                                            "id": signer.generate_uuid(),
                                            "name": "byte_edit",
                                            "image_uri_list": [image_uri],
                                            "image_list": [
                                                {
                                                    "type": "image",
                                                    "id": signer.generate_uuid(),
                                                    "source_from": "upload",
                                                    "platform_type": 1,
                                                    "name": "",
                                                    "image_uri": image_uri,
                                                    "width": 0,
                                                    "height": 0,
                                                    "format": "",
                                                    "uri": image_uri,
                                                }
                                            ],
                                            "strength": sample_strength,
                                        }
                                        for image_uri in image_uris
                                    ],
                                    "prompt_placeholder_info_list": [
                                        {
                                            "type": "",
                                            "id": signer.generate_uuid(),
                                            "ability_index": idx,
                                        }
                                        for idx, _ in enumerate(image_uris)
                                    ],
                                    "postedit_param": {
                                        "type": "",
                                        "id": signer.generate_uuid(),
                                        "generate_type": 0,
                                    },
                                },
                            },
                        }
                    ],
                },
                ensure_ascii=False,
            ),
            "http_common_info": {"aid": 513695},
        }

    def _generate_images_from_composition(
        self,
        prompt: str,
        image_inputs,
        negative_prompt: str = "",
    ) -> list[dict]:
        normalized = self._to_image_input_list(image_inputs)
        if not normalized:
            raise JimengGenerateException("image_inputs is required for image-to-image generation")
        if len(normalized) > 10:
            raise JimengGenerateException("image_inputs supports up to 10 images")

        image_uris = []
        for idx, image_input in enumerate(normalized, start=1):
            print(f"[INFO] Upload reference image {idx}/{len(normalized)}...")
            image_uri = self._upload_image_for_composition(image_input)
            image_uris.append(image_uri)

        request_data = self._build_composition_request(
            prompt=prompt,
            image_uris=image_uris,
            negative_prompt=negative_prompt,
        )
        result = self.client._call_api("/mweb/v1/aigc_draft/generate", request_data)
        history_id = result.get("aigc_data", {}).get("history_record_id")
        if not history_id:
            raise JimengGenerateException("Missing history_record_id for image composition")
        return self.client._poll_image_generation(history_id)
    
    def generate_base_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        image_inputs=None,
    ) -> Optional[str]:
        """
        Generate a base image with Jimeng.

        Args:
            prompt: Positive prompt.
            negative_prompt: Negative prompt.

        Returns:
            Saved image path, or None on failure.
        """
        if not prompt.strip():
            print("[ERROR] Prompt cannot be empty")
            return None

        normalized_inputs = self._to_image_input_list(image_inputs)
        print("[INFO] Starting image generation...")
        print(f"[INFO] Model: {self.model.value}")
        print(f"[INFO] Ratio: {self.ratio.value}")
        print(f"[INFO] Resolution: {self.resolution.value}")
        if normalized_inputs:
            print(f"[INFO] Mode: image-to-image ({len(normalized_inputs)} input image(s))")
        else:
            print("[INFO] Mode: text-to-image")
        print(f"[INFO] Prompt: {prompt[:100]}...")

        try:
            if normalized_inputs:
                images = self._generate_images_from_composition(
                    prompt=prompt,
                    image_inputs=normalized_inputs,
                    negative_prompt=negative_prompt,
                )
            else:
                images = self.client.generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    auto_download=False,
                )

            if not images:
                print("[ERROR] Generation failed: no images returned")
                return None

            print(f"[OK] Image generation succeeded, count={len(images)}")
            return self._save_image(images[0])

        except JimengAuthException as e:
            print(f"[ERROR] Authentication failed: {e}")
            _prompt_for_new_session()
            return None
        except JimengContentFilterException as e:
            print(f"[ERROR] Content filtered: {e}")
            return None
        except JimengInsufficientPointsException as e:
            print(f"[ERROR] Insufficient points: {e}")
            return None
        except JimengGenerateException as e:
            print(f"[ERROR] Generation failed: {e}")
            _run_upstream_check()
            return None
        except JimengAPIException as e:
            print(f"[ERROR] API call failed: {e}")
            if _is_session_related_error(str(e)):
                _prompt_for_new_session()
            else:
                _run_upstream_check()
            return None
        except Exception as e:
            print(f"[ERROR] Unexpected image generation error: {e}")
            _run_upstream_check()
            return None

    def _save_image(self, image_data: dict) -> Optional[str]:
        """
        淇濆瓨鍥剧墖鍒版湰鍦?
        
        Args:
            image_data: 鍥剧墖鏁版嵁瀛楀吀
        
        Returns:
            淇濆瓨鐨勫浘鐗囪矾寰勶紝澶辫触鍒欒繑鍥濶one
        """
        try:
            # 鑾峰彇鍥剧墖URL
            image_url = None
            if image_data.get("image", {}).get("large_images"):
                image_url = image_data["image"]["large_images"][0].get("image_url")
            elif image_data.get("common_attr", {}).get("cover_url"):
                image_url = image_data["common_attr"]["cover_url"]
            
            if not image_url:
                print("[ERROR] 鏈壘鍒板浘鐗嘦RL")
                return None
            
            # 涓嬭浇鍥剧墖
            import requests
            print(f"[INFO] 姝ｅ湪涓嬭浇鍥剧墖...")
            response = requests.get(image_url, timeout=30, verify=self.verify_tls)
            response.raise_for_status()
            
            # 鐢熸垚鏂囦欢鍚?
            timestamp = int(time.time())
            filename = f"base_image_{timestamp}.png"
            filepath = self.output_dir / filename
            
            # 淇濆瓨鍥剧墖
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            print(f"[OK] 鍥剧墖宸蹭繚瀛? {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"[ERROR] 淇濆瓨鍥剧墖澶辫触: {e}")
            return None


def main():
    """Simple local test entry."""
    sessionid = ""
    prompt = "Chinese ink flowing in water, black and white, slow motion, elegant."
    output_dir = "./outputs/images"

    generator = JimengImageGenerator(
        session_id=sessionid,
        output_dir=output_dir,
        model=ModelVersion.JIMENG_4_5,
        ratio=AspectRatio.RATIO_9_16,
        resolution=Resolution.RESOLUTION_2K,
        debug=True,
    )

    image_path = generator.generate_base_image(prompt)
    if image_path:
        print("\n[SUCCESS] Base image generated")
        print(f"[INFO] Image path: {image_path}")
    else:
        print("\n[FAILED] Base image generation failed")


if __name__ == "__main__":
    main()
