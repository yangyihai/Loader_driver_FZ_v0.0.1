# Loader_driver_FZ_v0.0.1
架构优化 ：v0.0.1 用 pyautogui、subprocess 控制终端和模拟键盘，v0.0.1 - 仿真版改用 rospy 发布消息，去除对外部终端依赖，同一进程内处理操作，更可靠高效。 依赖项精简 ：移除 pyautogui、pynput、psutil 等外部库，降低资源占用，不再创建多进程和终端窗口。 功能增强 ：添加命令历史记录，通过 command_history 存储最近 10 条命令，按 h 键可查看重用；新增 is_continuous 参数控制消息发布模式；用 select 模块实现非阻塞输入检测。
架构优化：直接使用ROS通信替代终端操作，v0.0.1通过pyautogui、subprocess控制终端和模拟键盘操作，v0.0.1-仿真版直接使用rospy发布消息，更加可靠和高效移除对外部终端的依赖，v0.0.1需要打开和管理新终端进程，仿真版完全在同一进程内处理所有操作
依赖项精简：减少了外部库依赖，移除了pyautogui、pynput、psutil等依赖降低了系统资源占用，不再创建多个进程和终端窗口
功能增强：添加命令历史记录，新增command_history存储最近10条命令，可通过h键查看和重用支持持续/单次消息发布模式，通过is_continuous参数控制消息发布方式使用非阻塞输入检测，使用select模块实现非阻塞方式检查用户输入
用户体验改进：菜单简化，移除了"服务启动"选项，精简了主菜单更直观的操作反馈，直接显示发布的消息内容统一的命令响应方式，所有命令使用相同的消息发布机制
执行效率提升：直接消息发布，避免了通过终端间接发送命令的延迟和不稳定性更精确的控制，可以精确控制消息发布频率(Rate参数)，目前固定以100Hz的频率发布
可维护性提升：代码结构更清晰，移除了与终端交互的复杂逻辑错误处理更稳健，减少了外部依赖带来的潜在问题
