@echo off
echo 正在安装依赖...
pip install -r requirements.txt

echo 启动爬虫程序...
python main.py

pause