import requests
import time
import json
import re
import logging
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlencode
from config import Config

class TikTokAPIClient:
    """TikTok API客户端类"""
    
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update(Config.DEFAULT_HEADERS)
        self.logger = logging.getLogger(__name__)
        self._session_initialized = False
        
    def initialize_session(self) -> bool:
        """
        初始化会话，访问主页获取必要的Cookie和token
        
        Returns:
            初始化是否成功
        """
        try:
            self.logger.info("正在初始化TikTok会话...")
            
            # 设置初始Cookie
            for name, value in Config.DEFAULT_COOKIES.items():
                self.session.cookies.set(name, value, domain='.tiktok.com')
            
            # 1. 访问主页
            home_response = self.session.get(
                Config.SESSION_INIT_CONFIG['home_page_url'],
                timeout=30
            )
            home_response.raise_for_status()
            
            # 等待一下模拟用户行为
            time.sleep(Config.SESSION_INIT_CONFIG['delay_between_requests'])
            
            # 2. 尝试提取新的token（如果页面中包含）
            self._extract_tokens_from_html(home_response.text)
            
            # 3. 访问搜索页面建立搜索上下文
            search_headers = self.session.headers.copy()
            search_headers['referer'] = Config.SESSION_INIT_CONFIG['home_page_url']
            
            search_response = self.session.get(
                Config.SESSION_INIT_CONFIG['search_page_url'],
                headers=search_headers,
                timeout=30
            )
            search_response.raise_for_status()
            
            self._session_initialized = True
            self.logger.info("TikTok会话初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"会话初始化失败: {str(e)}")
            return False
    
    def _extract_tokens_from_html(self, html_content: str):
        """从HTML中提取token信息"""
        try:
            # 尝试提取SIGI_STATE中的数据
            sigi_pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>'
            match = re.search(sigi_pattern, html_content)
            if match:
                try:
                    data = json.loads(match.group(1))
                    # 这里可以根据实际返回的数据结构提取需要的token
                    self.logger.debug("成功提取页面数据")
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            self.logger.debug(f"提取token时出错: {str(e)}")

    def make_request(self, api_name: str, dynamic_params: Dict[str, Any] = None) -> Optional[Dict]:
        """
        发起API请求
        
        Args:
            api_name: API配置名称
            dynamic_params: 动态参数字典
            
        Returns:
            API响应数据或None
        """
        try:
            # 确保会话已初始化
            if not self._session_initialized:
                if not self.initialize_session():
                    self.logger.error("会话初始化失败，无法继续请求")
                    return None
            
            api_config = Config.API_CONFIGS.get(api_name)
            if not api_config:
                raise ValueError(f"未找到API配置: {api_name}")
            
            # 构建请求参数
            params = self._build_params(api_config, dynamic_params or {})
            
            # 构建完整URL
            url = urljoin(Config.BASE_URL, api_config['url'])
            
            # 设置动态请求头
            keyword = dynamic_params.get('keyword', '') if dynamic_params else ''
            dynamic_headers = Config.get_dynamic_headers(keyword)
            
            # 发起请求
            response = self._send_request(
                method=api_config['method'],
                url=url,
                params=params,
                headers=dynamic_headers
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"API请求失败 {api_name}: {str(e)}")
            return None
    
    def _build_params(self, api_config: Dict, dynamic_params: Dict[str, Any]) -> Dict:
        """构建请求参数"""
        params = api_config['params_template'].copy()
        
        # 替换动态参数
        for key, value in params.items():
            if isinstance(value, str) and '{' in value and '}' in value:
                try:
                    params[key] = value.format(**dynamic_params)
                except KeyError as e:
                    raise ValueError(f"缺少必需的动态参数: {e}")
        
        return params
    
    def _send_request(self, method: str, url: str, params: Dict = None, headers: Dict = None) -> Dict:
        """发送HTTP请求"""
        max_retries = 3
        retry_delay = 1
        
        # 合并请求头
        request_headers = self.session.headers.copy()
        if headers:
            request_headers.update(headers)
        
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = self.session.get(
                        url, 
                        params=params, 
                        headers=request_headers,
                        timeout=30
                    )
                elif method.upper() == 'POST':
                    response = self.session.post(
                        url, 
                        data=params, 
                        headers=request_headers,
                        timeout=30
                    )
                else:
                    raise ValueError(f"不支持的HTTP方法: {method}")
                
                response.raise_for_status()
                
                # 记录响应信息用于调试
                self.logger.debug(f"响应状态码: {response.status_code}")
                self.logger.debug(f"响应头: {dict(response.headers)}")
                
                # 检查响应内容类型
                content_type = response.headers.get('content-type', '')
                if 'application/json' not in content_type:
                    self.logger.warning(f"响应不是JSON格式，内容类型: {content_type}")
                    self.logger.debug(f"响应内容前200字符: {response.text[:200]}")
                    
                    # 如果是HTML响应，可能是被重定向到登录页面
                    if 'text/html' in content_type:
                        raise ValueError("收到HTML响应，可能需要重新初始化会话")
                
                return response.json()
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"JSON解析失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                self.logger.debug(f"响应内容: {response.text[:500]}")
                
                if attempt < max_retries - 1:
                    # 重新初始化会话
                    self._session_initialized = False
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    raise
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    raise
    
    def close(self):
        """关闭会话"""
        self.session.close()
