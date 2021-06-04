
import string
import random

def generate_password(complexity: int = 1, pass_len: int = 4) -> str:
	"""
	Простой генератор пароля
	complexity: int (default 1): Сложность пароля
		1. Только цифры
		2. + буквы в нижнем регистре
		3. + буквы  верхнем регистре
		4. + специальные символы
	pass_len: int (default 4): длинна пароля
	Если длинна пароля = 0 возвращает пустую строку
	Если длинна пароля меньше 4 и при этом сложность выше 2
		сложность принимается за 2
	return: str - Пароль
	"""
	if pass_len == 0:
		return ""
	if pass_len < 4 and complexity > 2:
		complexity = 2
	if not isinstance(pass_len, int):
		pass_len = 4
	compl = {
		1 : string.digits,
		2 : string.digits+string.ascii_lowercase,
		3 : string.digits+string.ascii_letters,
		4 : string.printable[0:-6]
		}
	characters = compl.get(complexity, 1)
	password = random.choices(characters, k=pass_len)
	return "".join(password)