# TikTok 数据爬虫项目

本项目是一个用于从 TikTok 网站爬取数据的 Python 爬虫框架。它提供了灵活的配置选项，包括请求头管理、会话初始化、Selenium 集成以及调试功能，支持通过搜索接口获取 TikTok 内容数据。

## 配置说明

### 基础配置

- `BASE_URL`: TikTok 基础 URL，默认为 `https://www.tiktok.com`
- `OUTPUT_DIR`: 爬取数据保存目录，默认为 `output`

### 请求头配置 (`DEFAULT_HEADERS`)

模拟真实 Chrome 浏览器的 HTTP 请求头，包含：

- User-Agent: Chrome 137 浏览器标识
- Accept 系列: 内容类型和编码接受配置
- Sec-CH-UA: 浏览器客户端提示
- Referer: 动态生成，包含搜索关键词和时间戳

### 会话初始化配置 (`SESSION_INIT_CONFIG`)

- `home_page_url`: TikTok 首页 URL
- `search_page_url`: TikTok 搜索页 URL
- `required_cookies`: 必需的 Cookie 列表 `['ttwid', 'msToken']`
- `delay_between_requests`: 请求间延迟时间（秒），默认 2 秒

### Selenium 配置 (`SELENIUM_CONFIG`)

- `use_selenium`: 是否启用 Selenium，默认 True
- `headless`: 无头模式运行，默认 True
- `window_size`: 浏览器窗口大小 (1920, 1080)
- `user_data_dir`: Chrome 用户数据目录路径（可选）
- `executable_path`: ChromeDriver 路径（None 表示使用 PATH）
- `page_load_timeout`: 页面加载超时时间 30 秒
- `implicit_wait`: 隐式等待时间 10 秒

### 调试配置 (`DEBUG_CONFIG`)

- `save_response_content`: 是否保存响应内容，默认 True
- `response_dir`: 调试响应保存目录，默认 `debug_responses`
- `verbose_logging`: 详细日志输出，默认 True

### Cookie 配置 (`DEFAULT_COOKIES`)

**重要**: 包含 TikTok 会话所需的关键 Cookie，需要从真实浏览器获取：

- `_ttp`: TikTok 跟踪参数
- `tt_csrf_token`: CSRF 防护令牌
- `tt_chain_token`: 链式验证令牌
- `ttwid`: TikTok Web ID
- `msToken`: 微软令牌（关键）

### API 接口配置 (`API_CONFIGS`)

预定义的 API 配置模板，当前包含：

- `search_general_preview`: 搜索预览接口
  - URL: `/api/search/general/preview/`
  - 方法: GET
  - 包含 30+ 个参数，支持关键词动态替换

## 安装与设置

### 1. 环境准备

```bash
# 克隆项目到本地
git clone <repository_url>
cd 爬虫项目

# 安装依赖
pip install -r ./requests.txt
```

## 许可证

请确保在使用本项目时遵守相关法律法规和 TikTok 平台的使用条款。
