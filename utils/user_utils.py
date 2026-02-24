import re


def generate_username(full_name: str, phone: str) -> str:
    name_parts = full_name.strip().lower().split()
    if len(name_parts) < 2:
        raise ValueError('Full name must include first and last name')

    first_name = name_parts[0]
    last_name = name_parts[-1]
    last_4_digits = phone[-4:]
    return f'{first_name}.{last_name}{last_4_digits}'


def parse_promoted_class(promoted_to_class: str):
    parts = promoted_to_class.strip().lower().split()

    if len(parts) == 1:
        return (f'class{parts[0]}', 'general')

    if len(parts) == 2:
        class_num = parts[0]
        stream = parts[1]
        if class_num == 'dropper':
            return ('dropper', stream)
        return (f'class{class_num}', stream)

    raise ValueError('Invalid promoted_to_class format')


def is_valid_phone(phone: str) -> bool:
    return bool(re.match(r'^\d{10}$', phone))


def is_valid_email(email: str) -> bool:
    return bool(re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email))
