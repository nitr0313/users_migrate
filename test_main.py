
from main import User, UsersList, WindowsUsers, Password
import string
import unittest
from unittest import mock

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


def password_has(pwd) -> dict:
    """Возвращает виды символов в пароле

    Args:
        pwd ([type]): {}

    Raises:
        NotImplemented: [description]

    Returns:
        dict: [description]
    """
    result = {
        'digs': False,
        'lower_alpha': False,
        'upper_alphas': False,
        'printable_chars': False,        
        }
    digs = string.digits
    lower_alpha = string.ascii_lowercase
    upper_alphas = string.ascii_uppercase
    printable_chars = string.printable

    for a in pwd:
        if a in digs:
            result["digs"] = True
        elif a in lower_alpha:
            result["lower_alpha"] = True
        elif a in upper_alphas:
            result["upper_alphas"] = True
        elif a in printable_chars:
            result["printable_chars"] = True
        else:
            raise NotImplemented(f"Не должно такого быть! в пароле {a}")
    return result


class TestPassword(unittest.TestCase):
    
    def setUp(self):
        self.four_len_password = Password(pass_len=4)
        self.complexity_1_password = Password(complexity=1)
        self.complexity_2_password = Password(complexity=2)
        self.complexity_3_password = Password(complexity=3)
        self.complexity_4_password = Password(complexity=4)
        self.eight_len_password = Password()
        self.permanent_1234_password = Password(generate_pass=False, permanent_pass='1234')
        self.salt_and_permanent_1234_password = Password(generate_pass=False, permanent_pass='1234', use_salt=True)
        return super().setUp()

    def test_complexity_one_password(self):
        pwd = self.complexity_1_password.gen_pass()
        res = password_has(pwd)
        assert res["digs"]
        assert not any([res["lower_alpha"], res["upper_alphas"], res["printable_chars"]])


    def test_complexity_two_password(self):
        pwd = self.complexity_2_password.gen_pass()
        res = password_has(pwd)
        assert any([res["digs"], res["lower_alpha"]]) 
        assert not any([res["upper_alphas"], res["printable_chars"]])

    def test_complexity_three_password(self):
        pwd = self.complexity_3_password.gen_pass()
        res = password_has(pwd)
        assert any([res["digs"], res["lower_alpha"], res["upper_alphas"]])
        assert not res["printable_chars"]

    def test_complexity_four_password(self):
        pwd = self.complexity_4_password.gen_pass()
        res = password_has(pwd)
        assert any([res["digs"], res["lower_alpha"], res["upper_alphas"], res["upper_alphas"], res["printable_chars"]])

    def test_password_username_salt(self):
        pwd = self.salt_and_permanent_1234_password.get_pass(salt="username")
        assert pwd == 'username1234'

    def test_password_permanent_pass(self):
        pwd = self.permanent_1234_password.get_pass()
        assert pwd == '1234'

    def test_password_random_len(self):
        pwd = self.four_len_password.get_pass(salt="username")
        pwd2 = self.eight_len_password.get_pass()
        assert len(pwd) == 4
        assert len(pwd2) == 8
        

class TestUserList(unittest.TestCase):

    def setUp(self) -> None:
        self.user1 = User(username='u01', fullname='test ttt', active=True, groups=['group2', 'Пользователи'])
        self.user2 = User(username='u02', fullname='ttt Tests ', active=True, groups=['group2', 'Администраторы'])
        self.user3 = User(username='U01', fullname='ttt Tests ', active=True, groups=['group1', 'Администраторы'])
        self.users = UsersList()
        return super().setUp()

    def test_append(self):
        self.users.append(self.user1)
        self.users.append(self.user2)
        assert len(self.users) == 2
        result = self.users.append(self.user3)
        assert not result
        assert len(self.users) == 2
    
    def test_raise_on_extend(self):
        with self.assertRaises(AttributeError):
            self.users.extend([self.user1, self.user2])

    def test_append_bad_type_obj(self):
        with self.assertRaises(ValueError):
            self.users.append('a')

    def test_contains(self):
        self.users.append(self.user1)
        self.assertTrue(self.user1 in self.users)
        self.assertFalse(self.user2 in self.users)
        
    def test_search(self):
        self.users.append(self.user3)
        self.users.append(self.user2)
        self.assertEqual(len(self.users.get_users_by_attr('username', 'U02')), 1)
        self.assertEqual(len(self.users.get_users_by_attr('fullname', 'Tests')), 2)
        self.assertEqual(self.users.get_users_by_attr('username', 'U03'), None)
    
    def test_get_users_groups(self):
        self.users.append(self.user1)
        self.users.append(self.user2)
        groups = self.users.get_users_groups()
        self.assertEqual(type(groups), set)
        self.assertEqual(groups, {'Пользователи', 'Администраторы', 'group2'})

    def test_sub(self):
        users2 = UsersList()
        users2.append(self.user1)
        users2.append(self.user2)
        self.users.append(self.user1)
        users3 = users2-self.users
        assert isinstance(users3, UsersList)
        assert len(users3) == 1
        assert users3[0] == self.user2
        

class TestWindowsUsers(unittest.TestCase):
    ...
