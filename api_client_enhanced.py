import requests
import time
import json
import re
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urljoin, urlencode, quote
from config import Config

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class TikTokAPIClientEnhanced:
    """增强版TikTok API客户端类，支持Selenium备用方案"""
    
    def __init__(self, session: Optional[requests.Session] = None, use_selenium: bool = None):
        self.session = session or requests.Session()
        self.session.headers.update(Config.DEFAULT_HEADERS)
        self.logger = logging.getLogger(__name__)
        self._session_initialized = False
        self.driver = None
        
        # 确定是否使用Selenium
        self.use_selenium = use_selenium if use_selenium is not None else Config.SELENIUM_CONFIG['use_selenium']
        if self.use_selenium and not SELENIUM_AVAILABLE:
            self.logger.warning("⚠️  Selenium未安装，回退到requests模式")
            self.use_selenium = False
        
        # 确保调试目录存在
        if Config.DEBUG_CONFIG['save_response_content']:
            Config.ensure_debug_dir()
    
    def _init_selenium_driver(self) -> bool:
        """初始化Selenium WebDriver"""
        try:
            chrome_options = Options()
            
            if Config.SELENIUM_CONFIG['headless']:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument(f'--window-size={Config.SELENIUM_CONFIG["window_size"][0]},{Config.SELENIUM_CONFIG["window_size"][1]}')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # 提高加载速度
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 启用性能日志 - 使用更兼容的方式
            try:
                chrome_options.add_experimental_option('perfLoggingPrefs', {
                    'enableNetwork': True,
                    'enablePage': False,
                })
                chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
            except Exception as e:
                self.logger.warning(f"⚠️  无法启用性能日志: {str(e)}")
            
            # 设置用户代理
            chrome_options.add_argument(f'--user-agent={Config.DEFAULT_HEADERS["user-agent"]}')
            
            # 如果指定了用户数据目录
            if Config.SELENIUM_CONFIG['user_data_dir']:
                chrome_options.add_argument(f'--user-data-dir={Config.SELENIUM_CONFIG["user_data_dir"]}')
            
            # 创建WebDriver
            service = None
            if Config.SELENIUM_CONFIG['executable_path']:
                service = Service(Config.SELENIUM_CONFIG['executable_path'])
            
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(Config.SELENIUM_CONFIG['page_load_timeout'])
            self.driver.implicitly_wait(Config.SELENIUM_CONFIG['implicit_wait'])
            
            # 执行脚本隐藏webdriver特征
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 尝试启用网络域（如果支持）
            try:
                self.driver.execute_cdp_cmd('Network.enable', {})
                self.logger.debug("🌐 网络域启用成功")
            except Exception as e:
                self.logger.debug(f"⚠️  网络域启用失败: {str(e)}")
            
            self.logger.info("✅ Selenium WebDriver初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Selenium WebDriver初始化失败: {str(e)}")
            return False
    
    def initialize_session_with_selenium(self) -> bool:
        """使用Selenium初始化会话"""
        try:
            if not self._init_selenium_driver():
                return False
            
            self.logger.info("🤖 正在初始化TikTok会话...")
            
            # 访问主页
            self.logger.info("🏠 访问TikTok主页...")
            self.driver.get(Config.SESSION_INIT_CONFIG['home_page_url'])
            time.sleep(3)
            
            # 获取Cookie并转移到requests session
            selenium_cookies = self.driver.get_cookies()
            for cookie in selenium_cookies:
                self.session.cookies.set(
                    cookie['name'], 
                    cookie['value'], 
                    domain=cookie.get('domain', '.tiktok.com')
                )
            
            self.logger.info(f"🍪 获取到 {len(selenium_cookies)} 个Cookie")
            
            # 访问搜索页面
            search_url = f"{Config.SESSION_INIT_CONFIG['search_page_url']}?q=test"
            self.driver.get(search_url)
            time.sleep(2)
            
            # 再次获取Cookie（可能有新的）
            new_cookies = self.driver.get_cookies()
            for cookie in new_cookies:
                self.session.cookies.set(
                    cookie['name'], 
                    cookie['value'], 
                    domain=cookie.get('domain', '.tiktok.com')
                )
            
            self._session_initialized = True
            self.logger.info("✅ Selenium会话初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Selenium会话初始化失败: {str(e)}")
            return False
    
    def initialize_session(self) -> bool:
        """初始化会话"""
        if self.use_selenium:
            return self.initialize_session_with_selenium()
        else:
            return self._initialize_session_requests()
    
    def _initialize_session_requests(self) -> bool:
        """使用requests初始化会话"""
        try:
            self.logger.info("🌐 使用requests初始化TikTok会话...")
            
            # 设置初始Cookie
            for name, value in Config.DEFAULT_COOKIES.items():
                self.session.cookies.set(name, value, domain='.tiktok.com')
            
            # 访问主页
            home_response = self.session.get(
                Config.SESSION_INIT_CONFIG['home_page_url'],
                timeout=30
            )
            home_response.raise_for_status()
            
            self._save_debug_response(home_response, "home_page")
            
            time.sleep(Config.SESSION_INIT_CONFIG['delay_between_requests'])
            
            # 访问搜索页面
            search_headers = self.session.headers.copy()
            search_headers['referer'] = Config.SESSION_INIT_CONFIG['home_page_url']
            
            search_response = self.session.get(
                Config.SESSION_INIT_CONFIG['search_page_url'],
                headers=search_headers,
                timeout=30
            )
            search_response.raise_for_status()
            
            self._save_debug_response(search_response, "search_page")
            
            self._session_initialized = True
            self.logger.info("✅ requests会话初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ requests会话初始化失败: {str(e)}")
            return False
    
    def _save_debug_response(self, response, name_prefix: str):
        """保存调试响应内容"""
        if not Config.DEBUG_CONFIG['save_response_content']:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name_prefix}_{timestamp}.html"
            filepath = os.path.join(Config.DEBUG_CONFIG['response_dir'], filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"Status Code: {response.status_code}\n")
                f.write(f"Headers: {dict(response.headers)}\n")
                f.write(f"Cookies: {dict(response.cookies)}\n")
                f.write("="*50 + "\n")
                f.write(response.text)
            
            self.logger.debug(f"📁 调试响应已保存: {filepath}")
            
        except Exception as e:
            self.logger.debug(f"⚠️  保存调试响应失败: {str(e)}")

    def make_request(self, api_name: str, dynamic_params: Dict[str, Any] = None) -> Optional[Dict]:
        """发起API请求"""
        try:
            # 确保会话已初始化
            if not self._session_initialized:
                self.logger.info("🔄 初始化会话中...")
                if not self.initialize_session():
                    self.logger.error("❌ 会话初始化失败")
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
            
            self.logger.info(f"🌐 发起API请求: {api_config['method']} {api_config['url']}")
            self.logger.debug(f"📝 请求参数: {list(params.keys())}")
            
            # 发起请求
            response = self._send_request(
                method=api_config['method'],
                url=url,
                params=params,
                headers=dynamic_headers,
                api_name=api_name
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"💥 API请求异常 [{api_name}]: {str(e)}")
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
    
    def _send_request(self, method: str, url: str, params: Dict = None, headers: Dict = None, api_name: str = "") -> Dict:
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
                
                # 保存调试响应
                self._save_debug_response(response, f"api_{api_name}_{attempt+1}")
                
                self.logger.debug(f"📊 响应状态: {response.status_code}, 长度: {len(response.text)}")
                
                # 检查响应内容
                content_type = response.headers.get('content-type', '')
                self.logger.debug(f"📄 响应内容类型: {content_type}")
                
                if not response.text.strip():
                    self.logger.warning("⚠️  收到空响应")
                    raise ValueError("空响应")
                
                if 'application/json' not in content_type:
                    self.logger.warning(f"⚠️  响应不是JSON格式，内容类型: {content_type}")
                    self.logger.debug(f"📄 响应内容前500字符: {response.text[:500]}")
                    
                    # 尝试检查是否是重定向页面
                    if 'text/html' in content_type:
                        if 'login' in response.text.lower() or 'captcha' in response.text.lower():
                            raise ValueError("遇到登录页面或验证码，需要重新初始化会话")
                        elif response.text.strip().startswith('{'):
                            # 有时候content-type不正确但实际是JSON
                            self.logger.info("🔄 尝试解析为JSON（忽略content-type）")
                        else:
                            raise ValueError("收到HTML响应，可能被反爬虫拦截")
                
                # 尝试解析JSON
                try:
                    return response.json()
                except json.JSONDecodeError:
                    # 如果JSON解析失败，尝试提取可能的JSON内容
                    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                    if json_match:
                        try:
                            return json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass
                    raise
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"⚠️  JSON解析失败 (第{attempt + 1}/{max_retries}次): {str(e)}")
                if Config.DEBUG_CONFIG['verbose_logging']:
                    self.logger.debug(f"📄 响应内容: {response.text[:1000]}")
                
                if attempt < max_retries - 1:
                    # 重新初始化会话
                    self._session_initialized = False
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    raise
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"⚠️  请求失败 (第{attempt + 1}/{max_retries}次): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                else:
                    raise
    
    def close(self):
        """关闭客户端"""
        if self.driver:
            self.driver.quit()
        self.session.close()