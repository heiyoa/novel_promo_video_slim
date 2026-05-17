"""
即梦API核心模块

提供与即梦AI服务交互的核心功能，包括图片生成、轮询、下载等。
"""

import json
import time
import asyncio
import aiohttp
import requests
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path

from .constants import (
    AspectRatio, ModelVersion, Resolution, ImageFormat, ImageScene,
    DEFAULT_ASSISTANT_ID, BASE_URL, GenerateStatus, ErrorCodes, DEFAULT_CONFIG
)
from .signer import JimengSigner
from .exceptions import (
    JimengAPIException, JimengAuthException, JimengGenerateException,
    JimengNetworkException, JimengTimeoutException, JimengContentFilterException,
    JimengInsufficientPointsException
)


class JimengClient:
    """即梦API客户端"""
    
    def __init__(
        self,
        session_id: str,
        model: ModelVersion = DEFAULT_CONFIG["model"],
        ratio: AspectRatio = DEFAULT_CONFIG["ratio"],
        resolution: Resolution = DEFAULT_CONFIG["resolution"],
        sample_strength: float = DEFAULT_CONFIG["sample_strength"],
        timeout: int = DEFAULT_CONFIG["timeout"],
        max_poll_count: int = DEFAULT_CONFIG["max_poll_count"],
        poll_interval: int = DEFAULT_CONFIG["poll_interval"],
        debug: bool = False
    ):
        """
        初始化即梦客户端
        
        Args:
            session_id: 会话ID，用于身份验证
            model: 模型版本
            ratio: 图片宽高比
            resolution: 图片分辨率
            sample_strength: 采样强度
            timeout: 请求超时时间（秒）
            max_poll_count: 最大轮询次数
            poll_interval: 轮询间隔（秒）
            debug: 是否启用调试模式
        """
        if not session_id:
            raise JimengAuthException("session_id不能为空")
        
        self.session_id = session_id
        self.model = model
        self.ratio = ratio
        self.resolution = resolution
        self.sample_strength = sample_strength
        self.timeout = timeout
        self.max_poll_count = max_poll_count
        self.poll_interval = poll_interval
        self.debug = debug
        
        # 初始化签名器
        self.signer = JimengSigner(debug=debug)
        
        # 获取分辨率配置
        self.width, self.height = resolution.get_dimensions(ratio)
        self.image_ratio = ratio.ratio_code
        
        if debug:
            print(f"[即梦客户端] 初始化完成")
            print(f"  模型: {model.value}")
            print(f"  分辨率: {resolution.value} ({self.width}x{self.height})")
            print(f"  宽高比: {ratio.value}")
            print(f"  采样强度: {sample_strength}")
    
    def _call_api(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用即梦API
        
        Args:
            endpoint: API端点
            data: 请求数据
            
        Returns:
            Dict[str, Any]: 响应数据
            
        Raises:
            JimengAPIException: API调用失败
        """
        try:
            if self.debug:
                print(f"[API] 正在调用: {endpoint}")
            
            # 直接调用签名器获取请求头
            headers = self.signer.get_headers(endpoint, self.session_id)
            params = self.signer.get_request_params()
            
            # 发送请求
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                json=data,
                params=params,
                headers=headers,
                timeout=self.timeout,
                verify=False  # 禁用SSL验证以解决可能的证书问题
            )
            
            if self.debug:
                print(f"[响应] 状态: {response.status_code} {response.reason}")
            
            # 解析响应
            response_data = response.json()
            ret = response_data.get("ret")
            errmsg = response_data.get("errmsg")
            
            if ret == "0":
                return response_data.get("data", {})
            elif ret == "5000":
                raise JimengInsufficientPointsException(f"即梦积分可能不足，{errmsg}")
            elif ret == "2038":
                raise JimengContentFilterException("内容被过滤，请调整提示词")
            elif ret is not None:
                raise JimengAPIException(f"请求jimeng失败: {errmsg}", ret)
            else:
                return response_data
                
        except requests.exceptions.Timeout:
            raise JimengTimeoutException(f"请求超时 ({self.timeout}秒)")
        except requests.exceptions.ConnectionError as e:
            raise JimengNetworkException(f"网络连接失败: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise JimengNetworkException(f"网络请求失败: {str(e)}")
        except json.JSONDecodeError as e:
            raise JimengAPIException(f"响应解析失败: {str(e)}")
        except Exception as e:
            if isinstance(e, JimengAPIException):
                raise
            raise JimengAPIException(f"API调用失败: {str(e)}")
    
    def _build_generate_request(self, prompt: str, negative_prompt: str = "") -> Dict[str, Any]:
        """
        构建图片生成请求
        
        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            
        Returns:
            Dict[str, Any]: 请求数据
        """
        component_id = self.signer.generate_uuid()
        submit_id = self.signer.generate_uuid()
        
        request_data = {
            "extend": {
                "root_model": self.model.model_code,
            },
            "submit_id": submit_id,
            "metrics_extra": json.dumps({
                "promptSource": "custom",
                "generateCount": 1,
                "enterFrom": "click",
                "sceneOptions": [{
                    "type": "image",
                    "scene": "ImageBasicGenerate",
                    "modelReqKey": self.model.value,
                    "resolutionType": self.resolution.value,
                    "abilityList": [],
                    "reportParams": {
                        "enterSource": "generate",
                        "vipSource": "generate",
                        "extraVipFunctionKey": f"{self.model.value}-{self.resolution.value}",
                        "useVipFunctionDetailsReporterHoc": True,
                    },
                }],
                "generateId": submit_id,
                "isRegenerate": False,
            }),
            "draft_content": json.dumps({
                "type": "draft",
                "id": self.signer.generate_uuid(),
                "min_version": "3.0.2",
                "min_features": [],
                "is_from_tsn": True,
                "version": "3.3.4",
                "main_component_id": component_id,
                "component_list": [{
                    "type": "image_base_component",
                    "id": component_id,
                    "min_version": "3.0.2",
                    "aigc_mode": "workbench",
                    "metadata": {
                        "type": "",
                        "id": self.signer.generate_uuid(),
                        "created_platform": 3,
                        "created_platform_version": "",
                        "created_time_in_ms": str(int(time.time() * 1000)),
                        "created_did": "",
                    },
                    "generate_type": "generate",
                    "abilities": {
                        "type": "",
                        "id": self.signer.generate_uuid(),
                        "generate": {
                            "type": "",
                            "id": self.signer.generate_uuid(),
                            "core_param": {
                                "type": "",
                                "id": self.signer.generate_uuid(),
                                "model": self.model.model_code,
                                "prompt": prompt,
                                "negative_prompt": negative_prompt,
                                "seed": int(time.time() * 1000) % 100000000 + 2500000000,
                                "sample_strength": self.sample_strength,
                                "image_ratio": self.image_ratio,
                                "large_image_info": {
                                    "type": "",
                                    "id": self.signer.generate_uuid(),
                                    "min_version": "3.0.2",
                                    "height": self.height,
                                    "width": self.width,
                                    "resolution_type": self.resolution.value,
                                },
                                "intelligent_ratio": False,
                            },
                            "gen_option": {
                                "type": "",
                                "id": self.signer.generate_uuid(),
                                "generate_all": False,
                            },
                        },
                    },
                }],
            }),
            "http_common_info": {
                "aid": DEFAULT_ASSISTANT_ID,
            },
        }
        
        return request_data
    
    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        auto_download: bool = False,
        output_dir: str = "./downloads"
    ) -> List[Dict[str, Any]]:
        """
        生成图片
        
        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            auto_download: 是否自动下载图片
            output_dir: 图片保存目录
            
        Returns:
            List[Dict[str, Any]]: 生成的图片信息列表
            
        Raises:
            JimengGenerateException: 图片生成失败
        """
        if not prompt.strip():
            raise JimengGenerateException("提示词不能为空")
        
        if self.debug:
            print(f"[生成] 开始生成图片...")
            print(f"[提示词] {prompt[:100]}...")
        
        # 构建请求
        request_data = self._build_generate_request(prompt, negative_prompt)
        
        # 提交生成请求
        result = self._call_api('/mweb/v1/aigc_draft/generate', request_data)
        
        history_id = result.get("aigc_data", {}).get("history_record_id")
        if not history_id:
            raise JimengGenerateException("获取历史记录ID失败")
        
        if self.debug:
            print(f"[成功] 请求提交成功! history_id: {history_id}")
        
        # 轮询等待生成完成
        item_list = self._poll_image_generation(history_id)
        
        # 自动下载
        if auto_download and item_list:
            self._download_images(item_list, output_dir)
        
        return item_list
    
    def _poll_image_generation(self, history_id: str) -> List[Dict[str, Any]]:
        """
        轮询图片生成状态
        
        Args:
            history_id: 历史记录ID
            
        Returns:
            List[Dict[str, Any]]: 生成的图片列表
            
        Raises:
            JimengTimeoutException: 轮询超时
            JimengGenerateException: 生成失败
        """
        if self.debug:
            print("[轮询] 等待图片生成完成...")
        
        status = GenerateStatus.PENDING
        fail_code = None
        item_list = []
        poll_count = 0
        
        while poll_count < self.max_poll_count:
            time.sleep(self.poll_interval)
            poll_count += 1
            
            # 定期输出进度
            if self.debug and poll_count % 30 == 0:
                print(f"[轮询] 第 {poll_count} 次，状态: {status}，已生成: {len(item_list)} 张图片...")
            
            try:
                # 构建轮询请求
                poll_data = {
                    "history_ids": [history_id],
                    "image_info": {
                        "width": 2048,
                        "height": 2048,
                        "format": "webp",
                        "image_scene_list": [
                            {
                                "scene": "smart_crop",
                                "width": 360,
                                "height": 360,
                                "uniq_key": "smart_crop-w:360-h:360",
                                "format": "webp",
                            },
                            {
                                "scene": "smart_crop",
                                "width": 480,
                                "height": 480,
                                "uniq_key": "smart_crop-w:480-h:480",
                                "format": "webp",
                            },
                            {
                                "scene": "normal",
                                "width": 2400,
                                "height": 2400,
                                "uniq_key": "2400",
                                "format": "webp",
                            },
                        ],
                    },
                    "http_common_info": {
                        "aid": DEFAULT_ASSISTANT_ID,
                    },
                }
                
                poll_result = self._call_api('/mweb/v1/get_history_by_ids', poll_data)
                
                if not poll_result.get(history_id):
                    if self.debug and poll_count % 10 == 0:
                        print(f"[轮询] 没有找到historyId={history_id}的记录")
                    continue
                
                record = poll_result[history_id]
                status = record.get("status")
                fail_code = record.get("fail_code")
                item_list = record.get("item_list", [])
                
                # 检查是否已生成图片
                if item_list:
                    if self.debug:
                        print(f"[完成] 图片生成完成! 状态={status}，已生成 {len(item_list)} 张图片")
                    break
                
                # 检查生成失败
                if status == GenerateStatus.FAILED:
                    if fail_code == ErrorCodes.CONTENT_FILTERED:
                        raise JimengContentFilterException()
                    else:
                        raise JimengGenerateException(f"图片生成失败，错误代码: {fail_code}", fail_code)
                
            except JimengAPIException as e:
                if self.debug and poll_count % 10 == 0:
                    print(f"[错误] 轮询失败: {e}")
                continue
        
        if poll_count >= self.max_poll_count:
            raise JimengTimeoutException(f"生成超时: 轮询了 {poll_count} 次")
        
        return item_list
    
    def _download_images(self, item_list: List[Dict[str, Any]], output_dir: str):
        """
        下载图片
        
        Args:
            item_list: 图片信息列表
            output_dir: 保存目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for i, item in enumerate(item_list):
            try:
                # 获取图片URL
                image_url = None
                if item.get("image", {}).get("large_images"):
                    image_url = item["image"]["large_images"][0].get("image_url")
                elif item.get("common_attr", {}).get("cover_url"):
                    image_url = item["common_attr"]["cover_url"]
                
                if not image_url:
                    if self.debug:
                        print(f"[警告] 第 {i+1} 张图片没有找到URL")
                    continue
                
                # 下载图片
                response = requests.get(image_url, timeout=30, verify=False)  # 禁用SSL验证
                response.raise_for_status()
                
                # 保存图片
                timestamp = int(time.time())
                filename = f"generated_{timestamp}_{i+1}.webp"
                filepath = output_path / filename
                
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                if self.debug:
                    print(f"[下载] 成功: {filepath}")
                    
            except Exception as e:
                if self.debug:
                    print(f"[错误] 第 {i+1} 张图片下载失败: {e}")
    
    def upload_reference_image(self, image_path: str) -> Dict[str, Any]:
        """
        上传垫图
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            Dict[str, Any]: 上传结果，包含image_id或upload_uri
            
        Raises:
            JimengAPIException: 上传失败
        """
        # TODO: 实现垫图上传功能
        raise NotImplementedError("垫图上传功能暂未实现")
    
    async def generate_image_async(
        self,
        prompt: str,
        negative_prompt: str = "",
        auto_download: bool = False,
        output_dir: str = "./downloads"
    ) -> List[Dict[str, Any]]:
        """
        异步生成图片
        
        Args:
            prompt: 正向提示词
            negative_prompt: 负向提示词
            auto_download: 是否自动下载图片
            output_dir: 图片保存目录
            
        Returns:
            List[Dict[str, Any]]: 生成的图片信息列表
        """
        # TODO: 实现异步生成功能
        raise NotImplementedError("异步生成功能暂未实现")