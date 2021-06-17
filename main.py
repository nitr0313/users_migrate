import subprocess
from dataclasses import dataclass, field
from abc import ABC
from getpass import getpass
from utils import generate_password
import csv
import ctypes, sys, os
import wmi
import datetime
from tkinter import Tk
from tkinter.filedialog import askopenfilename



def is_admin() -> bool:
    """
    Проверка на административные парава

    Returns:
        bool: True если программа запущена с админскими правами, False если нет
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False 


class AccessViolation(Exception):
    """Ошибка доступа

    Args:
        Exception ([type]): [description]
    """
    pass 


@dataclass
class User:
    """
    DataClass информация о пользователе

    Raises:
        ValueError: При сравнении оба обьекта должны быть типа User

    Returns:
        [type]: [description]
    """
    username: str
    fullname: str = ""
    active: bool = False
    need_pwd: bool = True
    can_change_pwd: bool = False
    password: str = ""
    groups: list = field(default_factory=list)

    def get_hash_value(self):
        return self.username.lower()

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

    def as_cmd_dict(self) -> dict:
        """
        Создает словарь с ключами
        которые являллись атрибутами класса,
        добавляет несколько новых атрибутов

        Returns:
            dict: Словарь с данными пользователя
        """
        result = self.__dict__
        result['active'] = "yes" if result['active'] else "no"
        result['passwordchg'] = "yes" if result['can_change_pwd'] else "no"
        result['passwordreq'] = "yes" if result['need_pwd'] else "no"
        result['comment'] = "Migrated by python"
        result['expires'] = 'never'
        return self.__dict__

    def __eq__(self, object):
        """
        Сравнение двух обьектов одинакового типа

        Args:
            object ([type]): [description]

        Raises:
            ValueError: [description]

        Returns:
            [type]: [description]
        """
        if not isinstance(object, User):
            raise ValueError(f"Ожидаемый тип объекта: {type(self)}, получен: {type(object)}")
        return self.get_hash_value() == object.get_hash_value()


class UsersList(list):
    """
    Класс список пользователей

    Args:
        list ([type]): [description]
    """

    def __init__(self, *args, **kwargs):
        self.hash_item = set()
        super().__init__(*args, **kwargs)

    def append(self, obj) -> None or False:
        """
        Метод переопределен и проверяет есть ли уже 
        пользователь с таким username в списке перед добавлением
        Если есть то не добавляет и возвращает False

        Args:
            obj ([UsersList]):

        Returns:
            None or False
        """
        if obj.get_hash_value() in self.hash_item:
            print(f'Пользователь {obj} уже есть в списке!')
            return False
        self.hash_item.add(obj.get_hash_value())
        super().append(obj)
    
    def __getattribute__(self, name):
        if name in ['extend']:
            raise AttributeError('no such method')
        return super().__getattribute__(name)

    def __contains__(self, o: User) -> bool:
        return o.get_hash_value() in self.hash_item

    def item_in(self, value: str) -> bool:
        """[summary]
        Проверка на если такое имя в списке пользователей
        Args:
            value (str): В данном месте имя пользователя (username)

        Returns:
            bool: [description]
        """
        return value.lower() in self.hash_item

    def get_users_by_attr(self, attr: str, val: str):
        """
        Поиск пользователей по какому-то атрибуту
        get_users_by_attr('username', 'admin')

        Args:
            attr (str): Имя атрибута
            val (str): Искомое значение атрибута

        Returns:
            UsersList or None: Новый список пользователей
             или None если ничего не нашел
        """
        res = UsersList()
        for item in self:
            if not hasattr(item, attr):
                continue
            v1 = getattr(item, attr)
            if v1 and (v1 == val or val in v1):
                res.append(item)
        return res if res else None
    
    def get_users_groups(self) -> set:
        """
        Собирает все группы пользователей в оде set

        Returns:
            set: Множество груп мигрирующих пользователей
        """
        res = set()
        for user in self:
            res.update(user.groups)
        return res

    def __sub__(self, obj):
        """
        Вычитание словарей

        Args:
            obj (UsersList): Список пользователей

        Raises:
            ValueError: Возникаует если тип передаваемого
             обьекта отличается от исходного

        Returns:
            UsersList: Новый список пользователей
        """
        if not isinstance(obj, UsersList):
            raise ValueError(f"Оба объекта должны быть типа {type(self)}")
        result = UsersList()
        new_user_set = self.hash_item - obj.hash_item
        for user in self:
            if user.get_hash_value() in new_user_set:
                result.append(user)
        return result


class AbstractUsers(ABC):

    def __init__(self, path_users_file: str = None, ip_remote_comp: str = None):
        self.ip_remote_comp = ip_remote_comp
        self.system_users = UsersList()
        self.migration_users = UsersList()
        self.path_file = path_users_file
        self.local_groups = None

    def get_migration_users(self):
        if self.path_file is not None:
            return self.get_users_from_file()
        else:
            return self.get_remote_users()

    def run(self) -> None:
        self.get_local_users()
        self.get_migration_users()
        self.migration_users = self.migration_users - self.system_users
        # self.copy_users()

    def get_local_users(self) -> None:
        raise NotImplemented

    def copy_users(self):
        if input("Создаем новых пользователей? (Yes/No) ").lower() not in ['yes', 'да', '+', 'y']:
            print("Обработка прервана, пользователи не скопированы.")
            return
        for user in self.migration_users:
            self.create_user(user)
        if input("Добавляем новых пользователей в группы? (Yes/No) ").lower() not in ['yes', 'да', '+', 'y']:
            print("Обработка прервана, пользователи не добавлены в группы.")
            return
        for user in self.migration_users:
            self.add_user_to_group(user)

    def get_remote_users(self) -> None:
        raise NotImplemented

    def get_user_info(self):
        raise NotImplemented

    def add_to_os(self):
        raise NotImplemented
    
    def create_user(self, user: User):
        raise NotImplemented

    def add_user_to_group(self, user: User):
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
        print("Местные: ")
        if self.system_users is not None:
            for user in self.system_users:
                print(str(user))
        print("Пришлые: ")
        if self.migration_users is not None:
            for user in self.migration_users:
                print(str(user))


class Password:
    def __init__(self, generate_pass=True, complexity=2, pass_len=8, permanent_pass=None, use_salt=False):
        """
        generate_pass - bool Генерация пароля при каждом вызове get_pass
        complexity: int (default 1): Сложность пароля
            1. Только цифры
            2. + буквы в нижнем регистре
            3. + буквы  верхнем регистре
            4. + специальные символы
        pass_len: int (default 4): длинна пароля
        Если длинна пароля = 0 возвращает пустую строку
        Если длинна пароля меньше 4 и при этом сложность выше 2
            сложность принимается за 2
        permanent_pass - выдача постоянного пароля при generate_pass == False

        Если generate_pass - о при каждом вызове метода get_pass удет возвращаться новый пароль
        напротив generate_pass = False - будет возвращаться пустой пароль или permanent_pass 
        или тот пароль который вы передадите при вызове метода get_pass(pass='123')
        """
        self.permanent_pass = permanent_pass
        self.complexity = complexity
        self.pass_len = pass_len
        if generate_pass:
            self.get_pass = self.gen_pass
        else:
            self.get_pass = self.get_permanent_password


    def get_permanent_password(self, salt=None):
        if self.permanent_pass is None and self.use_salt:
            return str(salt)
        if self.permanent_pass is not None and not self.use_salt:     
            return self.permanent_pass
        return str(salt) + self.permanent_pass

    def gen_pass(self, salt=None):
        new_pass = generate_password(self.complexity, self.pass_len)
        return new_pass

    def get_pass(self, salt=None):
        ...


class WindowsUsers(AbstractUsers):

    def get_remote_users(self) -> list:
        """
        Получает пользователей удаленно с помощью wmi
        TODO Работает но очень медленно, проблема в ассоциации пользователя с группами

        """
        remote_user = input('Введите имя пользвателя: ')
        password = getpass('Введите пароль: ')
        user_pwd = self.set_users_password()
        pwd = user_pwd()
        c = wmi.WMI(self.ip_remote_comp, user=remote_user, password=password)

        for user_wmi_info in c.Win32_UserAccount():
            if user_wmi_info.Disabled:
                print(f"Пользователь {user_wmi_info.Caption} пропущен, так как аккаунт деактивирован")
                continue
            groups = [
                group.Caption.split("\\")[-1]
                for group in user_wmi_info.associators(wmi_result_class="Win32_Group")
            ]
            username = user_wmi_info.Caption.split("\\")[-1]
            user = User(
                username =  username,
                fullname =  user_wmi_info.Fullname,
                active = True,
                need_pwd =  user_wmi_info.PasswordRequired,
                can_change_pwd =  user_wmi_info.PasswordChangeable,
                password =  pwd.gen_pass(salt=username),
                groups =  groups
                )
            self.migration_users.append(user)

    def set_users_password(self):
        messages = {
            "1": ["Сгенерировать для каждого пользователя пароль",gen_pwd],
            "2": ["Задать для каждого пользователя один пароль",permanent_pwd],
            "3": ["Использовать в качестве пароля имя пользователя + постоянный пароль", gen_pwd2],
            "4": ["Использовать в качестве пароля имя пользователя",gen_pwd3],
        }
        print("Если у пользователя не задан пароль: ")
        for i, mess in messages.items():
            print(f"{i}. {mess[0]}")
        answer = input("-> ")
        if answer not in messages.keys():
            print("Вы выбрали не существуюший вариант, по умолчанию будет генерироваться пароль для каждого пользователя!")
            answer = 1
        return messages.get(answer)[1]

    @staticmethod
    def __execute_comand(cmd: list) -> str:
        if isinstance(cmd, list):
            cmd = ' '.join(cmd)
        resp = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if resp.returncode != 0 and resp.returncode != 2:
            if resp.returncode == 2 and "Системная ошибка 5" in resp.stdout.decode("866"):
                raise AccessViolation("Ошибка доступа, запустите программу с правами администратора.")
            elif resp.returncode != 2:
                raise ValueError(
                    f"Ошибка выполнения команды {cmd}! ErrorCode: {resp.returncode} " \
                    f"{resp.stdout.decode('866')}"
                    )
        return resp.stdout.decode('866')

    def create_user(self, user):
        cmd = [
            'net',
            'user {username} {password}',
            '/ADD',
            '/fullname:"{fullname}"',
            '/active:{active}',
            '/passwordreq:{passwordreq}',
            '/passwordchg:{passwordchg}',
            '/comment:"{comment}"',
            ]
        cmd = [ arg.format(**user.as_cmd_dict()) for arg in cmd ]
        print(cmd)
        # return
        text = self.__execute_comand(cmd=cmd)

    def get_local_groups(self) -> set:
        """
        Множество всех локальных групп в локальной системе

        Returns:
            set: [description]
        """
        cmd = ['net', 'localgroup']
        text = self.__execute_comand(cmd=cmd)        
        self.local_groups = self.pars_local_groups(text)

    def pars_local_groups(self, data: str):
        result = set()
        data = data.replace("\r\n", "\n")
        data = data.split('-')[-1]
        for group in data.split("\n"):
            if group.startswith("*"):
                result.add(group.strip("*"))
        return result

    def create_group(self, groupname: str) -> None:
        """
        Создать группу в локальной системе

        Args:
            groupname (str): [description]
        """
        ...

    def add_user_to_group(self, user: User) -> None:
        """
        Добавление пользоватлей в группы на локальной системе

        Args:
            user (User): пользователь

        Returns:
            [type]: [description]
        """
        self.get_local_groups()
        for group in self.migration_users.get_users_groups():
            if not group in self.local_groups:
                self.create_group(groupname=group)
        for group in user.groups:
            cmd = [
                'net',
                'localgroup "{group}" {username}'.format(group=group, username=user.username),
                '/ADD'
            ]
            text = self.__execute_comand(cmd=cmd)
            print(text)

    def get_local_users(self):
        """Получение всех локальных пользователей через net user
        """
        cmd = ["net", "user"]
        resp = self.__execute_comand(cmd=cmd)
        temp_user_list= self.__pars_users_list(resp)
        for usr in temp_user_list:
            user = self.get_user_info(usr)
            self.system_users.append(user)

    @staticmethod
    def __pars_users_list(data: str) -> list:
        """Парасинг ответа сервера на запрос (net user) списка пользователей

        Args:
            data (str): строка содержащая список всех пользователей

        Returns:
            list: список пользователей кроме встроенных учетных записей
        """
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
        """Получение информации по конкретному пользователю.

        Args:
            username (str): имя пользователя

        Returns:
            User: класс пользователя со всей достпной информацией
        """
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

    def get_users_from_file(self):
        """
        Загрузка пользователей из файла
        файл csv: 
        столбцы и примерные данные:
         username;fullname;active;need_pwd;can_change_pwd;password;groups
         admin; admin full name; 1; 1; 0; 12342; Администраторы, Пользователи удаленного рабочего стола
        """
        Tk().withdraw()
        filename = askopenfilename()
        user_pwd = self.set_users_password()
        pwd = user_pwd()
        with open(filename, 'r', encoding="utf8", newline='\n') as fl:
            reader = csv.DictReader(fl, delimiter=';', skipinitialspace=True)
            for row in reader:
                row['groups'] = [ group.strip() for group in row['groups'].split(",")]
                if not row['password'] or row['password'] is None:
                    row['password'] = pwd.gen_pass(salt=row["username"])
                user = User(**row)
                self.migration_users.append(user)

    def save_users_to_file(self):
        from_where = '' if self.ip_remote_comp is None else self.ip_remote_comp
        dt_now = datetime.datetime.now().strftime("%y-%m-%d_%H-%M")
        file_path = f"files\\users_from_{from_where}_{dt_now}.csv" #_{datetime.datetime.now().__str__()[:-7]}
        fieldnames = ['username','fullname','active','need_pwd','can_change_pwd','password','groups']
        with open(file_path, 'w+', encoding="utf8", newline='') as fl:
            writer = csv.DictWriter(fl, fieldnames=fieldnames, delimiter=';')
            writer.writeheader()
            for user in self.migration_users:
                usr = user.__dict__
                usr['groups'] = ",".join(usr['groups'])
                writer.writerow(usr)


def permanent_pwd():
    """
    Использование одного постоянного пароля
    """
    pwd = input("Введите постоянный пароль (Ex. 123) -> ")
    return Password(generate_pass=False, permanent_pass=pwd)

def gen_pwd():
    """
    Генерация полноценного пароля
    """
    complexity = int(input("Сложность пароля от 0 до 4 -> "))
    len_pwd = int(input("Длинна пароля от 1 до 16 -> "))
    return Password(complexity=complexity, pass_len=len_pwd)

def gen_pwd2():
    """
    Пароль -username+pwd
    """
    pwd = input("Введите постоянный пароль (Ex. 123) -> ")
    return Password(generate_pass=False, permanent_pass=pwd, use_salt=True)

def gen_pwd3():
    """
    Пароль - имя пользователя
    """
    return Password(generate_pass=False, use_salt=True)

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
    users = WindowsUsers(path_users_file='tests\\test_data.csv')
    users.run()
    pass

def add_users():
    pass

def users_list():
    pass

def users_groups():
    pass


def add_users_from_remote_pc():
    users = WindowsUsers(ip_remote_comp='192.168.0.251')
    users.run()

def exit_(msg=None):
    exit(msg)



menu = {
    '1': [
        'Добавить пользователей', {
            '1': ['Добавить пользователей из файла', add_users_from_file, {}],
            '2': ['Добавить вручную', add_users, {}],
            '3': ['Добавить автоматически с удаленного компьютера', add_users_from_remote_pc, {}],
            'default': ['В предыдущее меню', {}, {}],
        }
    ],
    '2': ['Cписок пользователей', users_list, {}],
    '3': ['Cписок груп', users_groups, {}],
    'default': ['Выход', exit_, {"msg": "Выбран выход из программы"}],
}

def load_menu():
    return menu

if __name__ == '__main__':
    # gen_password = Password()
    # print(gen_password.get_pass())
    # print(gen_password.get_pass(salt="username"))
    # q534zhhk
    # s3pre8h9

    # perm_password = Password(generate_pass=False, permanent_pass='1234')
    # print(perm_password.get_pass())
    # print(perm_password.get_pass(salt="username"))
    # 1234
    # username1234

    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    # start_menu = Menu()
    # start_menu.main_loop()

    # users = WindowsUsers(ip_remote_comp='192.168.0.251')
    users = WindowsUsers(path_users_file="tests/test_data.csv")
    # users = WindowsUsers()
    users.run()
    users.save_users_to_file()

    # new_users = users.migration_users.__sub__(users.system_users)
    # print("Новые пользователи: ")
    # for user in new_users:
    #     print(str(user))

    # user_info = users.get_user_info("admin")
    # print(user_info)
