# 装载机-仿真版-驱动层测试脚本
#!/usr/bin/env python3
import os
import time
import signal
import sys
import rospy
from loader_common.msg import State
from std_msgs.msg import Header
import select
import termios
import tty

# 全局变量
running_command = False
command_history = []  # 命令历史记录
# 提前初始化发布者，防止第一次发送消息失败
pwm_publisher = None
plc_publisher = None

# 值范围限制字典
value_ranges = {
    # pwm动作测试
    "swing": (-1000, 1000),
    "brake": (0, 1000),
    "boom": (-1000, 1000),
    "bucket": (-1000, 1000),
    "throttle": (-1000, 1000),
    "move_speed": (0, 1500),
    "hyd_torque": (0, 800),
    "hyd_speed": (0, 2000),
    # plc_command本体测试
    "PO": (0, 1),
    "RC": (0, 1),
    "P": (0, 1),
    "AL": (0, 3),
    "LT": (0, 1),
    "RT": (0, 1),
    "SS": (0, 1),
    "G": (-1, 2),
    "SP": (0, 1),
    "move_motor": (0, 2),
    "hydraulic_motor": (0, 2),
    "HS": (0, 1),
    "HL": (0, 2),  # 0关闭 1近光灯 2远光灯
    "WL": (0, 1),
    "wireless_stop": (0, 1),  # 0关 1开
    "Hn": (0, 1),  # 喇叭 0关闭 1开启
}

def clear_screen():
    """清屏函数"""
    os.system('cls' if os.name == 'nt' else 'clear')

def getch():
    """获取单个按键，无需按Enter"""
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ch

def ignore_signal(signum, frame):
    """忽略信号，防止Ctrl+C等中断脚本"""
    print("\n请使用'q'键返回上级菜单")

def publish_ros_message(topic, key, value, is_continuous=False):
    """发布ROS消息"""
    global running_command, pwm_publisher, plc_publisher
    running_command = True
    
    # 将命令添加到历史记录
    command = f"{topic} {key} {value}"
    if command not in command_history:
        command_history.append(command)
        if len(command_history) > 10:  # 只保存最近10条命令
            command_history.pop(0)
    
    # 创建消息
    msg = State()
    msg.header = Header()
    msg.key = [key]
    msg.data = [value]
    
    # 使用全局预先初始化的发布者
    if topic == "pwm":
        publisher = pwm_publisher
        rate_param = 100  # pwm消息默认发布频率
    else:  # plc_command
        publisher = plc_publisher
        rate_param = 1  # 单次发布
    
    rate = rospy.Rate(rate_param)
    
    if is_continuous:
        print(f"正在以{rate_param}Hz发布消息到/{topic}，按q键停止...")
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while running_command and not rospy.is_shutdown():
                publisher.publish(msg)
                rate.sleep()
                
                if select.select([sys.stdin], [], [], 0)[0]:
                    char = sys.stdin.read(1)
                    if char == 'q':
                        running_command = False
                        print("\n停止发布消息")
                        break
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    else:
        # 单次发布消息，多次发送以确保接收
        for _ in range(3):  # 尝试发送3次以确保消息被接收
            publisher.publish(msg)
            rospy.sleep(0.1)
        
        # 对于plc_command需要等待消息被接收
        if topic == "plc_command":
            rospy.sleep(0.5)
        print(f"已发布消息: /{topic} key={key} data={value}")
    
    running_command = False
    print("\n按任意键继续...")
    getch()  # 等待任意键继续

def get_valid_input(prompt, value_range=None):
    """获取有效的用户输入，q返回上一级而非退出脚本"""
    value = ""
    print(prompt, end='', flush=True)
    while True:
        char = getch()
        
        # q键直接返回
        if char.lower() == 'q':
            print("q")  # 回显q
            return 'q'
            
        # h键显示历史
        elif char.lower() == 'h':
            print("\nh")  # 回显h
            show_command_history()
            print(prompt + value, end='', flush=True)
            
        # 回车键确认
        elif char == '\r' or char == '\n':
            print()  # 换行
            if not value:
                print("请输入有效的数字，或输入q返回上一级菜单，h显示历史命令")
                print(prompt, end='', flush=True)
                continue
                
            try:
                int_value = int(value)
                if value_range and (int_value < value_range[0] or int_value > value_range[1]):
                    print(f"\n输入超出范围，请输入 {value_range[0]} 到 {value_range[1]} 之间的值")
                    value = ""
                    print(prompt, end='', flush=True)
                    continue
                return int_value
            except ValueError:
                print("\n请输入有效的数字")
                value = ""
                print(prompt, end='', flush=True)
                
        # 退格键
        elif char == '\x7f' or char == '\b':
            if value:
                value = value[:-1]
                print("\b \b", end='', flush=True)  # 删除前一个字符
                
        # 数字输入
        elif char.isdigit() or (char == '-' and not value):
            value += char
            print(char, end='', flush=True)  # 回显输入的字符

def get_menu_choice(max_option):
    """获取菜单选择，支持多位数字输入"""
    choice = ""
    while True:
        char = getch()
        
        # q键直接返回
        if char.lower() == 'q':
            print("q")  # 回显q
            return 'q'
            
        # h键显示历史
        elif char.lower() == 'h':
            print("h")  # 回显h
            return 'h'
            
        # 回车键确认
        elif char == '\r' or char == '\n':
            if not choice:
                continue
                
            try:
                int_choice = int(choice)
                if 1 <= int_choice <= max_option:
                    print()  # 换行
                    return int_choice
                else:
                    print(f"\n请输入1-{max_option}之间的数字")
                    choice = ""
            except ValueError:
                print("\n请输入有效的数字")
                choice = ""
                
        # 退格键
        elif char == '\x7f' or char == '\b':
            if choice:
                choice = choice[:-1]
                print("\b \b", end='', flush=True)  # 删除前一个字符
                
        # 数字输入
        elif char.isdigit():
            choice += char
            print(char, end='', flush=True)  # 回显输入的字符

def show_command_history():
    """显示命令历史记录"""
    if not command_history:
        print("\n历史记录为空")
        print("\n按任意键继续...")
        getch()
        return
    
    print("\n命令历史记录:")
    for i, cmd in enumerate(command_history, 1):
        print(f"{i}: {cmd}")
    
    print("\n输入数字重新执行对应命令，或按q返回: ", end='', flush=True)
    
    choice = ""
    while True:
        char = getch()
        if char == 'q':
            print("q")
            return
        elif char.isdigit():
            choice += char
            print(char, end='', flush=True)
        elif char == '\r' or char == '\n':
            print()
            if choice and choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(command_history):
                    cmd = command_history[idx]
                    print(f"执行命令: {cmd}")
                    parts = cmd.split()
                    if len(parts) == 3:
                        topic, key, value = parts
                        publish_ros_message(topic, key, int(value))
            return
        elif char == '\x7f' or char == '\b':
            if choice:
                choice = choice[:-1]
                print("\b \b", end='', flush=True)  # 删除前一个字符

def display_main_menu():
    """显示主菜单"""
    clear_screen()
    print("\n驱动层测试选择：")
    print("1.下位机 - pwm动作测试")
    print("2.下位机 - plc_command 本体测试")
    print("3.查看历史命令")
    print("q.退出脚本")
    print("\n请选择功能（输入数字后按Enter确认）: ", end='', flush=True)

def display_pwm_menu():
    """显示pwm动作测试菜单"""
    clear_screen()
    print("\n下位机 - pwm动作测试:")
    print("1.转向-swing")
    print("2.大臂-boom")
    print("3.铲斗-bucket")
    print("4.刹车-brake")
    print("5.行进电机扭矩-throttle")
    print("6.行进电机转速-move_speed")
    print("7.液压电机扭矩-hyd_torque")
    print("8.液压电机转速-hyd_speed")
    print("h.查看历史命令")
    print("q.返回主菜单")
    print("\n请选择功能（输入数字后按Enter确认）: ", end='', flush=True)

def display_plc_menu():
    """显示plc_command本体测试菜单"""
    clear_screen()
    print("\n下位机 - plc_command 本体测试:")
    print("1.遥控急停-wireless_stop")
    print("2.本地远程切换-RC")
    print("3.整车上电/下电-PO")
    print("4.驻车刹车开启/关闭(开1关0)-P")
    print("5.液压锁-HS")
    print("6.电子手刹开启/关-SP")
    print("7.软急停开启/关闭-SS")
    print("8.档位-G")
    print("9.行进电机模式：1：转速模式 2：扭矩模式-move_motor")
    print("10.液压电机模式：1：转速模式 2：扭矩模式-hydraulic_motor")
    print("11.喇叭-Hn")
    print("12.声光报警开启/关闭-AL")
    print("13.左转灯开启/关闭-LT")
    print("14.右转灯开启/关闭-RT")
    print("15.车灯-HL(0关闭 1近光灯 2远光灯)")
    print("16.工作大灯-WL")
    print("h.查看历史命令")
    print("q.返回主菜单")
    print("\n请选择功能（输入数字后按Enter确认）: ", end='', flush=True)

def handle_pwm_command(choice):
    """处理pwm动作测试命令"""
    pwm_options = {
        1: ("swing", "转向"),
        2: ("boom", "大臂"),
        3: ("bucket", "铲斗"),
        4: ("brake", "刹车"),
        5: ("throttle", "行进电机扭矩"),
        6: ("move_speed", "行进电机转速"),
        7: ("hyd_torque", "液压电机扭矩"),
        8: ("hyd_speed", "液压电机转速")    }
    
    if choice not in pwm_options:
        return
    
    option, description = pwm_options[choice]
    value_range = value_ranges[option]
    
    clear_screen()
    print(f"\n{description}测试 (范围: {value_range[0]}~{value_range[1]}) - 按q返回上一级菜单")
    value = get_valid_input(f"请输入{description}的值: ", value_range)
    
    if value == 'q':
        return
    
    # 发布pwm消息
    publish_ros_message("pwm", option, value, is_continuous=True)

def handle_plc_command(choice):
    """处理plc_command本体测试命令"""
    plc_options = {
        1: ("wireless_stop", "遥控急停"),
        2: ("RC", "本地远程切换", 1),  # 固定值1
        3: ("PO", "整车上电/下电"),
        4: ("P", "驻车刹车开启/关闭"),
        5: ("HS", "液压锁"),
        6: ("SP", "电子手刹开启/关"),
        7: ("SS", "软急停开启/关闭"),
        8: ("G", "档位"),
        9: ("move_motor", "行进电机模式"),
        10: ("hydraulic_motor", "液压电机模式"),
        11: ("Hn", "喇叭"),
        12: ("AL", "声光报警开启/关闭"),
        13: ("LT", "左转灯开启/关闭"),
        14: ("RT", "右转灯开启/关闭"),
        15: ("HL", "车灯"), # 0关闭 1近光灯 2远光灯
        16: ("WL", "工作大灯")
    }
    
    if choice not in plc_options:
        return
    
    if len(plc_options[choice]) == 3:
        option, description, fixed_value = plc_options[choice]
        value = fixed_value
    else:
        option, description = plc_options[choice]
        value_range = value_ranges[option]
        
        clear_screen()
        if option == "HL":
            print(f"\n{description}测试 (0:关闭 1:近光灯 2:远光灯) - 按q返回上一级菜单")
        elif option == "Hn":
            print(f"\n{description}测试 (0:关闭 1:开启) - 按q返回上一级菜单")
        else:
            print(f"\n{description}测试 (范围: {value_range[0]}~{value_range[1]}) - 按q返回上一级菜单")
            
        value = get_valid_input(f"请输入{description}的值: ", value_range)
        
        if value == 'q':
            return
    
    # 发布plc_command消息
    publish_ros_message("plc_command", option, value)

def main():
    global running_command, pwm_publisher, plc_publisher
    
    # 忽略常见的中断信号，确保只有q键可以中断
    signal.signal(signal.SIGINT, ignore_signal)  # Ctrl+C
    signal.signal(signal.SIGTSTP, ignore_signal)  # Ctrl+Z
    
    # 初始化ROS节点
    rospy.init_node('loader_test_node', anonymous=True, disable_signals=True)
    
    # 提前初始化发布者，防止第一次发送消息失败
    pwm_publisher = rospy.Publisher('/pwm', State, queue_size=10)
    plc_publisher = rospy.Publisher('/plc_command', State, queue_size=10)
    rospy.sleep(1.0)  # 等待发布者完全初始化
    
    clear_screen()
    print("驱动层测试脚本已启动")
    print("注意: 使用'q'键可以随时终止当前命令并返回上级菜单")
    print("\n按任意键继续...")
    getch()
    
    # 主循环
    while True:
        display_main_menu()
        choice = get_menu_choice(3)
        
        if choice == 'q':
            print("\n退出脚本...")
            break
        elif choice == 'h':
            show_command_history()
        elif choice == 1:
            # pwm动作测试
            while True:
                display_pwm_menu()
                pwm_choice = get_menu_choice(8)
                
                if pwm_choice == 'q':
                    break
                elif pwm_choice == 'h':
                    show_command_history()
                elif 1 <= pwm_choice <= 8:
                    handle_pwm_command(pwm_choice)
        elif choice == 2:
            # plc_command本体测试
            while True:
                display_plc_menu()
                plc_choice = get_menu_choice(16)
                
                if plc_choice == 'q':
                    break
                elif plc_choice == 'h':
                    show_command_history()
                elif 1 <= plc_choice <= 16:
                    handle_plc_command(plc_choice)
        elif choice == 3:
            # 显示历史命令
            show_command_history()

    # 确保清理资源
    running_command = False
    print("脚本已完全退出")

if __name__ == "__main__":
    main()