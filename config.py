import os
from typing import Dict, Any


class Config:
    """配置类，管理爬虫的各种配置信息"""

    # 基础配置
    BASE_URL = "https://www.tiktok.com"
    OUTPUT_DIR = "output"

    # 请求头配置 - 基于真实浏览器请求
    DEFAULT_HEADERS = {
        'accept': '*/*',
        'accept-encoding': 'gzip, deflate, br, zstd',
        'accept-language': 'zh-CN,zh;q=0.9',
        'priority': 'u=1, i',
        'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'referer': 'https://www.tiktok.com/search?q={encoded_keyword}&t={timestamp}',
    }

    # 会话初始化配置
    SESSION_INIT_CONFIG = {
        'home_page_url': 'https://www.tiktok.com/',
        'search_page_url': 'https://www.tiktok.com/search',
        'required_cookies': ['ttwid', 'msToken'],  # 必需的Cookie
        'delay_between_requests': 2,  # 请求间延时（秒）
    }

    # Selenium配置（备用方案）
    SELENIUM_CONFIG = {
        'use_selenium': True,  # 是否使用Selenium
        'headless': True,  # 是否使用无头模式
        'window_size': (1920, 1080),
        'user_data_dir': None,  # Chrome用户数据目录
        'executable_path': None,  # ChromeDriver路径（None表示使用PATH中的）
        'page_load_timeout': 30,
        'implicit_wait': 10,
    }

    # 调试配置
    DEBUG_CONFIG = {
        'save_response_content': True,  # 保存响应内容用于调试
        'response_dir': 'debug_responses',  # 调试响应保存目录
        'verbose_logging': True,  # 详细日志
    }

    # Cookie模板 - 这些需要从实际浏览器会话中获取
    DEFAULT_COOKIES = {
        '_ttp': '2vV4zN7ZygBNQJlQtM6CcdeIfPL',
        'tt_csrf_token': 'aPIPAvdW-GPcG1_H_3c--BGo50U7snH5WobI',
        'tt_chain_token': '932vB9HT9qs8U4cSGHWzMA==',
        'tiktok_webapp_theme': 'light',
        'tiktok_webapp_theme_source': 'auto',
        'ttwid': '1%7CZFeozfzCzKlJovy7Drl21RGq76qe7Ew1m_KtoXG5RD4%7C1749619229%7Cac149883af3f182681fb9979c2d03abd1a61a008a37a0f7095561017d47169a5',
        'msToken': '2vMjxT8CeBOWIGl_8dpJ0N1lQ7mPFGjKJeQ6kXGNdBvZHgh93f5p52c_Y7IJo6xl68e3rUZ2HCZ0vj1LOALaxQVtsE-DyL0mCEDs4m4rb2QOQTwrs6efbh6LO0XVBgfXpmDhVyyFyGn7k_o7V6T4JF-8lnQ='
    }

    # 接口配置模板
    API_CONFIGS = {
        'search_general_preview': {
            'url': '/api/search/general/preview/',
            'method': 'GET',
            'params_template': {
                'WebIdLastTime': '1749619197',
                'aid': '1988',
                'app_language': 'zh-Hans',
                'app_name': 'tiktok_web',
                'browser_language': 'zh-CN',
                'browser_name': 'Mozilla',
                'browser_online': 'true',
                'browser_platform': 'Win32',
                'browser_version': '5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
                'channel': 'tiktok_web',
                'cookie_enabled': 'true',
                'data_collection_enabled': 'false',
                'device_id': '7514557204474791431',
                'device_platform': 'web_pc',
                'focus_state': 'true',
                'from_page': 'search',
                'history_len': '3',
                'is_fullscreen': 'false',
                'is_page_visible': 'true',
                'keyword': '{keyword}',  # 动态参数
                'odinId': '7514557006495155218',
                'os': 'windows',
                'priority_region': '',
                'referer': 'https://www.google.com.hk/',
                'region': 'JP',
                'root_referer': 'https://www.google.com.hk/',
                'screen_height': '965',
                'screen_width': '1715',
                'tz_name': 'Asia/Shanghai',
                'user_is_login': 'false',
                'webcast_language': 'zh-Hans'
            },
            'dynamic_params': ['keyword']  # 需要动态替换的参数
        }
    }

    @classmethod
    def ensure_output_dir(cls):
        """确保输出目录存在"""
        if not os.path.exists(cls.OUTPUT_DIR):
            os.makedirs(cls.OUTPUT_DIR)

    @classmethod
    def ensure_debug_dir(cls):
        """确保调试目录存在"""
        if not os.path.exists(cls.DEBUG_CONFIG['response_dir']):
            os.makedirs(cls.DEBUG_CONFIG['response_dir'])

    @classmethod
    def get_dynamic_headers(cls, keyword: str = "", timestamp: str = "") -> Dict[str, str]:
        """
        获取动态请求头，包含编码后的关键词和时间戳

        Args:
            keyword: 搜索关键词
            timestamp: 时间戳

        Returns:
            动态请求头字典
        """
        import urllib.parse
        import time

        headers = cls.DEFAULT_HEADERS.copy()

        if keyword:
            encoded_keyword = urllib.parse.quote(keyword)
            current_timestamp = timestamp or str(int(time.time() * 1000))
            headers['referer'] = f'https://www.tiktok.com/search?q={encoded_keyword}&t={current_timestamp}'

        return headers
