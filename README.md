# Loader_driver_FZ_v0.0.1
架构优化 ：v0.0.1 用 pyautogui、subprocess 控制终端和模拟键盘，v0.0.1 - 仿真版改用 rospy 发布消息，去除对外部终端依赖，同一进程内处理操作，更可靠高效。 依赖项精简 ：移除 pyautogui、pynput、psutil 等外部库，降低资源占用，不再创建多进程和终端窗口。 功能增强 ：添加命令历史记录，通过 command_history 存储最近 10 条命令，按 h 键可查看重用；新增 is_continuous 参数控制消息发布模式；用 select 模块实现非阻塞输入检测。
