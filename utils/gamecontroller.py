from typing import Literal, Tuple, Optional
import os
import logging
import time
import psutil
import win32gui
import ctypes


class GameController:
    def __init__(self, game_path: str, process_name: str, window_name: str, window_class: Optional[str], logger: Optional[logging.Logger] = None) -> None:
        self.game_path = os.path.normpath(game_path)
        self.process_name = process_name
        self.window_name = window_name
        self.window_class = window_class
        self.logger = logger

    def log_debug(self, message: str) -> None:
        """记录调试日志，如果logger不为None"""
        if self.logger is not None:
            self.logger.debug(message)

    def log_info(self, message: str) -> None:
        """记录信息日志，如果logger不为None"""
        if self.logger is not None:
            self.logger.info(message)

    def log_error(self, message: str) -> None:
        """记录错误日志，如果logger不为None"""
        if self.logger is not None:
            self.logger.error(message)

    def log_warning(self, message: str) -> None:
        """记录警告日志，如果logger不为None"""
        if self.logger is not None:
            self.logger.warning(message)

    def start_game(self) -> bool:
        """启动游戏"""
        if not os.path.exists(self.game_path):
            self.log_error(f"游戏路径不存在：{self.game_path}")
            return False

        if not os.system(f'cmd /C start "" "{self.game_path}"'):
            self.log_info(f"游戏启动：{self.game_path}")
            return True
        else:
            self.log_error("启动游戏时发生错误")
            return False

    @staticmethod
    def terminate_named_process(target_process_name, termination_timeout=10):
        """
        根据进程名终止属于当前用户的进程。

        参数:
        - target_process_name (str): 要终止的进程名。
        - termination_timeout (int, optional): 终止进程前等待的超时时间（秒）。

        返回值:
        - bool: 如果成功终止进程则返回True，否则返回False。
        """
        system_username = os.getlogin()  # 获取当前系统用户名
        # 遍历所有运行中的进程
        for process in psutil.process_iter(attrs=["pid", "name"]):
            # 检查当前进程名是否匹配并属于当前用户
            if target_process_name in process.info["name"]:
                process_username = process.username().split("\\")[-1]  # 从进程所有者中提取用户名
                if system_username == process_username:
                    proc_to_terminate = psutil.Process(process.info["pid"])
                    proc_to_terminate.terminate()  # 尝试终止进程
                    proc_to_terminate.wait(termination_timeout)  # 等待进程终止

    def stop_game(self) -> bool:
        """终止游戏"""
        try:
            # os.system(f'taskkill /f /im {self.process_name}')
            self.terminate_named_process(self.process_name)
            self.log_info(f"游戏终止：{self.process_name}")
            return True
        except Exception as e:
            self.log_error(f"终止游戏时发生错误：{e}")
            return False

    @staticmethod
    def set_foreground_window_with_retry(hwnd):
        """尝试将窗口设置为前台，失败时先最小化再恢复。"""

        def toggle_window_state(hwnd, minimize=False):
            """最小化或恢复窗口。"""
            SW_MINIMIZE = 6
            SW_RESTORE = 9
            state = SW_MINIMIZE if minimize else SW_RESTORE
            ctypes.windll.user32.ShowWindow(hwnd, state)

        toggle_window_state(hwnd, minimize=False)
        if ctypes.windll.user32.SetForegroundWindow(hwnd) == 0:
            toggle_window_state(hwnd, minimize=True)
            toggle_window_state(hwnd, minimize=False)
            if ctypes.windll.user32.SetForegroundWindow(hwnd) == 0:
                raise Exception("Failed to set window foreground")

    def switch_to_game(self) -> bool:
        """将游戏窗口切换到前台"""
        try:
            hwnd = win32gui.FindWindow(self.window_class, self.window_name)
            if hwnd == 0:
                self.log_debug("游戏窗口未找到")
                return False
            self.set_foreground_window_with_retry(hwnd)
            self.log_info("游戏窗口已切换到前台")
            return True
        except Exception as e:
            self.log_error(f"激活游戏窗口时发生错误：{e}")
            return False

    def get_resolution(self) -> Optional[Tuple[int, int]]:
        """检查游戏窗口的分辨率"""
        try:
            hwnd = win32gui.FindWindow(self.window_class, self.window_name)
            if hwnd == 0:
                self.log_debug("游戏窗口未找到")
                return None
            _, _, window_width, window_height = win32gui.GetClientRect(hwnd)
            return window_width, window_height
        except IndexError:
            self.log_debug("游戏窗口未找到")
            return None

    def shutdown(self, action: Literal['Exit', 'Loop', 'Shutdown', 'Sleep', 'Hibernate'], delay: int = 60) -> bool:
        """
        终止游戏并在指定的延迟后执行系统操作：关机、休眠、睡眠。

        参数:
            action: 要执行的系统操作。
            delay: 延迟时间，单位为秒，默认为60秒。

        返回:
            操作成功执行返回True，否则返回False。
        """
        self.stop_game()
        if action not in ["Shutdown", "Hibernate", "Sleep"]:
            return True

        self.log_warning(f"将在{delay}秒后开始执行系统操作：{action}")
        time.sleep(delay)  # 暂停指定的秒数

        try:
            if action == 'Shutdown':
                os.system("shutdown /s /t 0")
            elif action == 'Sleep':
                # 必须先关闭休眠，否则下面的指令不会进入睡眠，而是优先休眠
                os.system("powercfg -h off")
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                os.system("powercfg -h on")
            elif action == 'Hibernate':
                os.system("shutdown /h")
            self.log_info(f"执行系统操作：{action}")
            return True
        except Exception as e:
            self.log_error(f"执行系统操作时发生错误：{action}, 错误：{e}")
            return False
