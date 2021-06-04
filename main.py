import subprocess
from dataclasses import dataclass, field
from abc import ABC
import wmi
from getpass import getpass

@dataclass
class User:
    username: str
    fullname: str = ""
    active: bool = False
    need_pwd: bool = True
    can_change_pwd: bool = False
    password: str = ""
    groups: list = field(default_factory=list)

    def __str__(self):
        result = f'{"-"*50}\n' \
            f'Имя пользователя: {self.username}\n' \
            f'Полное имя: {self.fullname}\n' \
            f'Активен: {self.active}\n' \
            f'Нужен пароль: {self.need_pwd}\n' \
            f'Может сменить пароль: {self.can_change_pwd}\n' \
            f'Пароль: {self.password}\n' \
            f'Локальные группы: {" | ".join(self.groups):<100}\n' \
            f'{"_"*50}'
        return result




class AbstractUsers(ABC):

    def __init__(self, path_users_file: str =None, ip_remote_comp: str = None):
        self.ip_remote_comp = ip_remote_comp
        self.system_users_list = self.get_local_users()
        self.users_list = []
        self.path_file = path_users_file

    def get_local_users(self) -> list:
        raise NotImplemented

    def get_remote_users(self) -> list:
        raise NotImplemented

    def get_user_info(self):
        raise NotImplemented

    def add_to_os(self):
        raise NotImplemented

    def get_users_from_file(self):
        raise NotImplemented

    def get_user_from_stdi(self):
        """
        пОЛУЧЕНИЕ информации о пользователе из input
        """
        raise NotImplemented 

    def __str__(self):
        return self

    def prn(self):
        for user in self.system_users_list:
            print(str(user))



def strip_(username):
    return username.strip()

class WindowsUsers(AbstractUsers):
    users_list = []
    # def __init__(self, ip_remote_comp=None):
    #     super().__init__(ip_remote_comp)

    def get_remote_users(self):
        user = input('Введите имя пользвателя: ')
        password = getpass('Введите пароль: ')
        c = wmi.WMI(self.ip_remote_comp, user=user, password=password)
        for user in c.Win32_UserAccount():
            print(user)

    @staticmethod
    def __execute_comand(cmd: list) -> str:
        resp = subprocess.run(cmd, stdout=subprocess.PIPE)
        if resp.returncode != 0:
            raise ValueError(
                f"Ошибка выполнения команды {cmd}! ErrorCode: {resp.returncode} " /
                f"{resp.stdout.decode('866')}"
                )
        return resp.stdout.decode('866')

    def get_local_users(self):
        cmd = ["net", "user"]
        resp = self.__execute_comand(cmd=cmd)
        temp_user_list= self.__pars_users_list(resp)
        result = []
        for usr in temp_user_list:
            user = self.get_user_info(usr)
            result.append(user)
        return result

    @staticmethod
    def __pars_users_list(data: str) -> list:
        data = data.replace('\r\n', '\n').strip().split('--\n')
        data.pop(0)
        data = data[0]
        result= []
        for user_name in data.split():
            if 'Команда' in user_name:
                break
            if user_name.strip() in ['Гость', 'Администратор']:
                continue
            result.append(user_name)
        return result

    def get_user_info(self, username: str) -> User:
        cmd = ["net","user",username]
        resp = self.__execute_comand(cmd=cmd)
        user_info = self.__pars_users_info(resp)
        user_info["username"] = username
        user = User(**user_info)
        return user

    @staticmethod
    def __pars_users_info(data: str) -> dict:
        data = data.replace("\r\n", "\n")
        result : dict = dict(
            fullname=None,
            active=None,
            need_pwd=None,
            can_change_pwd=None,
            groups=[]
            )
        groups_start = False
        for row in data.split('\n'):
            if 'Полное имя' in row:
                result["fullname"] = row[11:].strip()
            if 'Учетная запись активна' in row:
                result["active"] = True if row.split()[-1] == "Yes" else False
            if 'Требуется пароль' in row:
                result["need_pwd"] = True if row.split()[-1] == "Yes" else False
            if 'Пользователь может изменить пароль' in row:
                result["can_change_pwd"] = True if row.split()[-1] == "Yes" else False
            if 'Членство в глобальных группах' in row:
                groups_start = False
                break
            if 'Членство в локальных группах' in row or groups_start:
                groups_start = True
                result["groups"].append(row.split('*')[-1].strip())
        return result


class Menu:
    """
    Класс реализующий меню на основе словаря
    """
    def __init__(self):
        self.menu = load_menu()
        self.current_menu = self.menu.copy()
        self.path_ = []
        self.default = self.__set_default()

    def __set_default(self):
        if 'default' in self.current_menu:
            return self.current_menu['default']
        return self.current_menu[sorted(list(self.current_menu.keys()))[-1]]

    def main_loop(self):
        while True:
            self.__print_current_menu()
            ans = input("Выберите действие: ")
            os.system('cls||clear')
            self.__get__(ans)

    def __print_current_menu(self):
        """
        Вывод на консоль текущего меню
        :return:
        """
        for key, value in self.current_menu.items():
            if key.isdigit():
                print(f"{key}. {value[0]}")
            else:
                print(f"По умолчанию {value[0]}")

    def __get__(self, key: str):
        value = self.current_menu.get(key, self.default)
        if isinstance(value[1], dict):
            if value[1]:
                self.current_menu = value[1]
                self.path_.append(key)
            else:
                self.current_menu = self.__get_parent()
            self.default = self.__set_default()
        else:
            value[1](**value[2])

    def __get_parent(self) -> dict:
        """
        Возвразает родительское меню
        :return:
        """
        temp_result = self.menu.copy()
        if self.path_:
            self.path_.pop()
            for index in range(len(self.path_)):
                menu_item = self.path_[index]
                temp_result = temp_result[menu_item][1]
        return temp_result


def add_users_from_file():
    pass

def add_users():
    pass

def users_list():
    pass

def users_groups():
    pass

def exit_(msg=None):
    exit(msg)

menu = {
    '1': [
        'Добавить пользователей', {
            '1': ['Добавить пользователей из файла', add_users_from_file, {}],
            '2': ['Добавить вручную', add_users, {}],
            'default': ['В предыдущее меню', {}, {}],
        }
    ],
    '2': ['Cписок пользователей', users_list, {}],
    '3': ['Cписок груп', users_groups, {}],
    'default': ['Выход', exit_, {"msg": "Выбран выход из программы"}],
}



if __name__ == '__main__':
    users = WindowsUsers(ip_remote_comp='192.168.0.251')
    # users = WindowsUsers()
    users.get_remote_users()
    users.prn()

    # user_info = users.get_user_info("admin")
    # print(user_info)
