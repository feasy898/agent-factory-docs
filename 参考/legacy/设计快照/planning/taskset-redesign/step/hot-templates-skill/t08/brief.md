# brief — t08 非法 platform 与空白 topic

任务摘要：验证非法 platform（bilibili）与空白 topic（strip 后为空）均触发 exit 2 且零产物。

可机判判据：
- bilibili 组退出码 = 2，输出目录未被创建
- 空白 topic 组退出码 = 2，输出目录未被创建
- 两组 stderr 均含 [gen.py] 错误： 或 argparse 英文报错
- 合法对照组（platform=dy, topic=测试, points=[a]）退出码 = 0 且产物齐全
