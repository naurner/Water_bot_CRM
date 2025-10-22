import re


def validate_kyrgyzstan_phone(phone):
    """
    Валидация и форматирование номера телефона Кыргызстана
    Принимает различные форматы и приводит к: +996 (XXX) XXX XXX
    """
    # Удаляем все символы кроме цифр и +
    digits = re.sub(r'[^\d]', '', phone.lstrip('+'))

    # Нормализуем номер к формату 996XXXXXXXXX
    if digits.startswith('0'):
        digits = '996' + digits[1:]
    elif not digits.startswith('996'):
        digits = '996' + digits

    # Проверяем длину (должно быть 12 цифр: 996 + 9 цифр)
    if len(digits) != 12:
        return None

    # Форматируем: +996 (XXX) XXX XXX
    return f"+{digits[:3]} ({digits[3:6]}) {digits[6:9]} {digits[9:]}"


def format_kyrgyzstan_phone(phone):
    """Форматирование номера телефона (без строгой валидации)"""
    return validate_kyrgyzstan_phone(phone) or phone
