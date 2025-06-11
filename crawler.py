import logging
import time
import json
import os
import re
from typing import Dict, List, Optional
from api_client_enhanced import TikTokAPIClientEnhanced
from data_processor import DataProcessor


class TikTokCrawler:
    """TikTok爬虫主类"""

    def __init__(self, use_selenium: bool = None):
        self.api_client = TikTokAPIClientEnhanced(use_selenium=use_selenium)
        self.data_processor = DataProcessor()
        self.logger = logging.getLogger(__name__)

    def crawl_search_preview(self, keyword: str) -> Optional[str]:
        """
        爬取搜索预览接口

        Args:
            keyword: 搜索关键词

        Returns:
            保存的Excel文件路径或None
        """
        try:
            self.logger.info(f"📝 任务开始 - 关键词: {keyword}")

            # 首先尝试API请求
            self.logger.info("🌐 尝试API直接请求...")
            response_data = self.api_client.make_request(
                api_name='search_general_preview',
                dynamic_params={'keyword': keyword}
            )

            # 如果API请求失败，尝试使用Selenium直接获取数据
            if response_data is None and self.api_client.use_selenium:
                self.logger.info("🤖 API请求失败，启用Selenium模式...")
                response_data = self._crawl_with_selenium_direct(keyword)

            if response_data is None:
                self.logger.error(f"❌ 数据获取失败 - 关键词: {keyword}")
                return None

            # 统计获取的数据量
            data_count = 0
            if isinstance(response_data, dict):
                if 'sug_list' in response_data:
                    data_count = len(response_data['sug_list'])
                elif 'search_results' in response_data:
                    data_count = len(response_data['search_results'])
                elif isinstance(response_data.get('data'), list):
                    data_count = len(response_data['data'])

            self.logger.info(f"📊 数据获取成功 - 共 {data_count} 条记录")

            # 保存为Excel
            self.logger.info("💾 开始保存Excel文件...")
            excel_path = self.data_processor.save_to_excel(
                data=response_data,
                api_name='search_preview',
                keyword=keyword
            )

            self.logger.info(f"✅ 文件保存成功: {os.path.basename(excel_path)}")
            return excel_path

        except Exception as e:
            self.logger.error(f"💥 爬取异常 - 关键词: {keyword}, 错误: {str(e)}")
            return None

    def _crawl_with_selenium_direct(self, keyword: str) -> Optional[Dict]:
        """
        使用Selenium直接从页面获取数据

        Args:
            keyword: 搜索关键词

        Returns:
            提取的数据或None
        """
        try:
            if not self.api_client.driver:
                self.logger.error("🤖 Selenium驱动未初始化")
                return None

            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from urllib.parse import quote

            # 构建搜索URL
            encoded_keyword = quote(keyword)
            search_url = f"https://www.tiktok.com/search?q={encoded_keyword}"

            self.logger.info(f"🌍 访问搜索页面: {search_url}")
            self.api_client.driver.get(search_url)

            self.logger.info("⏳ 等待页面加载...")
            time.sleep(5)

            # 等待搜索结果加载
            try:
                WebDriverWait(self.api_client.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "[data-e2e='search-card-item'], [data-e2e='search-video-item']"))
                )
            except:
                self.logger.warning("搜索结果未加载完成，继续尝试提取数据")

            self.logger.info("🔍 尝试拦截网络请求...")
            response_data = self._intercept_network_requests()

            if response_data:
                self.logger.info("✅ 网络请求拦截成功")
                return response_data

            self.logger.info("🔧 网络拦截失败，尝试页面元素提取...")
            return self._extract_data_from_page_elements(keyword)

        except Exception as e:
            self.logger.error(f"🤖 Selenium数据获取失败: {str(e)}")
            return None

    def _intercept_network_requests(self) -> Optional[Dict]:
        """
        从浏览器网络请求中拦截API响应

        Returns:
            拦截到的API响应数据或None
        """
        try:
            # 获取浏览器日志
            logs = self.api_client.driver.get_log('performance')

            api_responses = []

            for log in logs:
                try:
                    message = json.loads(log['message'])
                    if message['message']['method'] == 'Network.responseReceived':
                        url = message['message']['params']['response']['url']
                        # 检查多种可能的API路径
                        if any(api_path in url for api_path in [
                            '/api/search/general/preview/',
                            '/api/search/item/',
                            '/api/search/',
                            '/api/recommend/',
                            'search'
                        ]):
                            request_id = message['message']['params']['requestId']

                            # 尝试获取响应体
                            try:
                                response_body = self.api_client.driver.execute_cdp_cmd(
                                    'Network.getResponseBody',
                                    {'requestId': request_id}
                                )

                                if response_body and 'body' in response_body:
                                    body_data = json.loads(
                                        response_body['body'])
                                    api_responses.append({
                                        'url': url,
                                        'data': body_data
                                    })
                                    self.logger.info(f"成功拦截API响应: {url}")

                            except Exception as e:
                                self.logger.debug(f"获取响应体失败 {url}: {str(e)}")
                                continue
                except Exception as e:
                    self.logger.debug(f"解析日志失败: {str(e)}")
                    continue

            # 返回最相关的API响应
            if api_responses:
                # 优先返回search/general/preview的响应
                for response in api_responses:
                    if '/api/search/general/preview/' in response['url']:
                        return response['data']

                # 如果没有找到，返回第一个包含数据的响应
                for response in api_responses:
                    if response['data']:
                        return response['data']

            return None

        except Exception as e:
            self.logger.debug(f"网络请求拦截失败: {str(e)}")
            return None

    def _extract_data_from_page_elements(self, keyword: str) -> Optional[Dict]:
        """从页面元素中提取数据

        Args:
            keyword: 搜索关键词

        Returns:
            提取的数据字典或None
        """
        try:
            from selenium.webdriver.common.by import By

            # 等待页面完全加载
            time.sleep(3)

            # 尝试多种选择器来查找视频元素
            selectors = [
                "[data-e2e='search-card-item']",
                "[data-e2e='search-video-item']",
                "[data-e2e*='search']",
                "div[class*='DivItemContainer']",
                "div[class*='video']",
                "a[href*='/video/']",
                "div[data-e2e]",
                ".tiktok-yz6ijl-DivWrapper",
                ".tiktok-x6y88p-DivItemContainerV2"
            ]

            video_elements = []
            for selector in selectors:
                try:
                    elements = self.api_client.driver.find_elements(
                        By.CSS_SELECTOR, selector)
                    if elements:
                        video_elements = elements
                        self.logger.info(
                            f"使用选择器找到元素: {selector} ({len(elements)}个)")
                        break
                except Exception as e:
                    self.logger.debug(f"选择器失败 {selector}: {str(e)}")
                    continue

            # 如果还是没找到，尝试查找所有包含链接的div
            if not video_elements:
                try:
                    all_divs = self.api_client.driver.find_elements(
                        By.TAG_NAME, "div")
                    video_elements = [
                        div for div in all_divs if div.find_elements(By.TAG_NAME, "a")]
                    self.logger.info(f"通过div+a查找到 {len(video_elements)} 个潜在元素")
                except Exception as e:
                    self.logger.debug(f"备用查找失败: {str(e)}")

            extracted_data = {
                'keyword': keyword,
                'search_results': [],
                'total_count': len(video_elements),
                'extraction_method': 'selenium_page_elements',
                'timestamp': int(time.time()),
                'page_url': self.api_client.driver.current_url,
                'page_title': self.api_client.driver.title
            }

            self.logger.info(f"🎯 找到 {len(video_elements)} 个页面元素")

            # 保存页面截图用于调试
            try:
                screenshot_path = f"debug_responses/page_screenshot_{int(time.time())}.png"
                self.api_client.driver.save_screenshot(screenshot_path)
                self.logger.debug(f"页面截图已保存: {screenshot_path}")
            except Exception as e:
                self.logger.debug(f"保存截图失败: {str(e)}")

            for i, element in enumerate(video_elements[:20]):  # 限制提取前20个
                try:
                    # 滚动到元素可见区域
                    try:
                        self.api_client.driver.execute_script(
                            "arguments[0].scrollIntoView(true);", element)
                        time.sleep(0.1)
                    except:
                        pass

                    # 基本元素信息
                    video_data = {
                        'index': i,
                        'element_text': element.text.strip()[:500] if element.text else '',
                        'element_tag': element.tag_name,
                        'element_class': element.get_attribute('class') or '',
                        'data_e2e': element.get_attribute('data-e2e') or '',
                        'element_id': element.get_attribute('id') or '',
                    }

                    # 尝试提取链接
                    try:
                        link_elements = element.find_elements(By.TAG_NAME, 'a')
                        if link_elements:
                            href = link_elements[0].get_attribute('href')
                            if href and 'tiktok.com' in href:
                                video_data['video_url'] = href
                    except:
                        pass

                    # 尝试提取图片
                    try:
                        img_elements = element.find_elements(
                            By.TAG_NAME, 'img')
                        if img_elements:
                            src = img_elements[0].get_attribute('src')
                            if src:
                                video_data['thumbnail_url'] = src
                    except:
                        pass

                    # 尝试提取标题和描述
                    try:
                        # 查找标题元素
                        title_selectors = [
                            'h1', 'h2', 'h3', '[data-e2e*="title"]', 'strong', '.title']
                        for selector in title_selectors:
                            try:
                                title_elements = element.find_elements(
                                    By.CSS_SELECTOR, selector)
                                if title_elements and title_elements[0].text.strip():
                                    video_data['title'] = title_elements[0].text.strip(
                                    )
                                    break
                            except:
                                continue
                    except:
                        pass

                    # 只保存有用的数据
                    if (video_data.get('video_url') or
                        video_data.get('element_text') or
                            video_data.get('title')):
                        extracted_data['search_results'].append(video_data)

                except Exception as e:
                    self.logger.debug(f"提取第{i}个元素数据失败: {str(e)}")
                    continue

            # 如果没有提取到有效数据，尝试获取页面源码中的结构化数据
            if not extracted_data['search_results']:
                try:
                    page_source = self.api_client.driver.page_source
                    # 查找可能的JSON数据
                    json_matches = re.findall(
                        r'\{[^{}]*"id"[^{}]*\}', page_source)
                    if json_matches:
                        # 保存前5个匹配项
                        extracted_data['raw_json_data'] = json_matches[:5]
                        self.logger.info(
                            f"从页面源码中提取到 {len(json_matches)} 个JSON片段")
                except Exception as e:
                    self.logger.debug(f"提取页面JSON失败: {str(e)}")

            if extracted_data['search_results'] or extracted_data.get('raw_json_data'):
                self.logger.info(
                    f"📋 成功提取 {len(extracted_data['search_results'])} 条结构化数据")
                return extracted_data
            else:
                self.logger.warning("⚠️  未能提取到有效数据，返回页面基本信息")
                # 返回基本页面信息
                return {
                    'keyword': keyword,
                    'extraction_method': 'page_info_only',
                    'page_url': self.api_client.driver.current_url,
                    'page_title': self.api_client.driver.title,
                    'page_text_preview': self.api_client.driver.find_element(By.TAG_NAME, "body").text[:1000],
                    'timestamp': int(time.time())
                }

        except Exception as e:
            self.logger.error(f"📄 页面元素提取失败: {str(e)}")
            return None

    def crawl_multiple_keywords(self, keywords: List[str]) -> List[str]:
        """
        批量爬取多个关键词

        Args:
            keywords: 关键词列表

        Returns:
            成功保存的CSV文件路径列表
        """
        successful_files = []

        for keyword in keywords:
            try:
                csv_path = self.crawl_search_preview(keyword)
                if csv_path:
                    successful_files.append(csv_path)

                # 添加延时避免请求过快
                import time
                time.sleep(1)

            except Exception as e:
                self.logger.error(f"处理关键词 {keyword} 时出错: {str(e)}")
                continue

        return successful_files

    def add_api_config(self, api_name: str, config: Dict):
        """
        动态添加新的API配置（为后续扩展准备）

        Args:
            api_name: API名称
            config: API配置
        """
        from config import Config
        Config.API_CONFIGS[api_name] = config
        self.logger.info(f"已添加新的API配置: {api_name}")

    def close(self):
        """关闭爬虫，释放资源"""
        self.api_client.close()
