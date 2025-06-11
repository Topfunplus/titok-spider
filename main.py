import logging
import os
from datetime import datetime
from crawler import TikTokCrawler

def setup_logging():
    """设置优化的日志配置"""
    # 创建日志目录 - 移到最前面
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建自定义格式器
    class ColoredFormatter(logging.Formatter):
        """彩色日志格式器"""
        
        # ANSI颜色代码
        COLORS = {
            'DEBUG': '\033[36m',      # 青色
            'INFO': '\033[32m',       # 绿色
            'WARNING': '\033[33m',    # 黄色
            'ERROR': '\033[31m',      # 红色
            'CRITICAL': '\033[35m',   # 紫色
        }
        RESET = '\033[0m'
        
        def format(self, record):
            # 简化模块名显示
            name_parts = record.name.split('.')
            if len(name_parts) > 1:
                record.name = name_parts[-1]  # 只显示最后一部分
            
            # 格式化时间
            record.asctime = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
            
            # 应用颜色
            color = self.COLORS.get(record.levelname, '')
            record.levelname = f"{color}{record.levelname:<7}{self.RESET}"
            record.name = f"\033[94m{record.name:<12}\033[0m"  # 蓝色模块名
            
            return super().format(record)
    
    # 控制台处理器 - 彩色输出
    console_handler = logging.StreamHandler()
    console_formatter = ColoredFormatter(
        '🕐 %(asctime)s | %(levelname)s | %(name)s | %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # 文件处理器 - 详细日志
    file_handler = logging.FileHandler(os.path.join(log_dir, 'crawler.log'), encoding='utf-8')
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-15s | %(funcName)-15s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # 错误日志处理器
    error_handler = logging.FileHandler(os.path.join(log_dir, 'error.log'), encoding='utf-8')
    error_handler.setFormatter(file_formatter)
    error_handler.setLevel(logging.ERROR)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # 设置第三方库日志级别
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def print_banner():
    """打印程序启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🚀 TikTok 数据爬虫工具                      ║
║                                                              ║
║  功能特性:                                                    ║
║  • 🔍 智能搜索数据抓取                                        ║
║  • 📊 Excel格式数据导出                                       ║
║  • 📅 按日期自动分类存储                                      ║
║  • 🤖 Selenium + API 双重保障                                ║
║  • 🛡️  完善的错误处理机制                                     ║
║                                                              ║
║  作者: GitHub Copilot  |  版本: v1.0.0                       ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def main():
    """主函数"""
    print_banner()
    
    try:
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("🚀 TikTok爬虫启动中...")
        
        # 创建爬虫实例
        crawler = TikTokCrawler()
        
        try:
            # 示例：单个关键词爬取
            print("\n" + "="*60)
            keyword = input("🔍 请输入搜索关键词: ").strip()
            
            if not keyword:
                print("❌ 关键词不能为空！")
                return
                
            print("="*60)
            logger.info(f"🎯 开始处理关键词: {keyword}")
            
            excel_path = crawler.crawl_search_preview(keyword)
            
            if excel_path:
                print("\n" + "🎉" + "="*58 + "🎉")
                print(f"✅ 爬取成功！")
                print(f"📄 文件路径: {excel_path}")
                print(f"📁 存储目录: output/{datetime.now().strftime('%Y-%m-%d')}/")
                print(f"🕐 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("🎉" + "="*58 + "🎉\n")
                logger.info(f"✅ 任务完成 - 文件已保存: {excel_path}")
            else:
                print("\n❌ 爬取失败，请检查网络连接和参数配置")
                logger.error("❌ 爬取任务失败")
            
            # 询问是否继续
            while True:
                continue_choice = input("\n🔄 是否继续爬取其他关键词？(y/n): ").strip().lower()
                if continue_choice in ['n', 'no', '否']:
                    break
                elif continue_choice in ['y', 'yes', '是']:
                    keyword = input("🔍 请输入新的搜索关键词: ").strip()
                    if keyword:
                        logger.info(f"🎯 开始处理关键词: {keyword}")
                        excel_path = crawler.crawl_search_preview(keyword)
                        if excel_path:
                            print(f"✅ 爬取成功！文件已保存: {excel_path}")
                            logger.info(f"✅ 任务完成 - 文件已保存: {excel_path}")
                        else:
                            print("❌ 爬取失败")
                            logger.error("❌ 爬取任务失败")
                    else:
                        print("❌ 关键词不能为空！")
                else:
                    print("请输入 y 或 n")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  用户中断程序")
            logger.warning("⚠️  用户手动中断程序")
        except Exception as e:
            print(f"\n💥 程序执行出错: {str(e)}")
            logger.error(f"💥 程序执行出错: {str(e)}", exc_info=True)
        finally:
            logger.info("🔚 正在关闭爬虫...")
            crawler.close()
            print("\n👋 程序已退出，感谢使用！")
            logger.info("👋 程序正常退出")
            
    except Exception as e:
        print(f"\n💥 程序初始化失败: {str(e)}")
        print("请检查程序配置和依赖是否正确安装")
        input("按任意键退出...")

if __name__ == "__main__":
    main()
