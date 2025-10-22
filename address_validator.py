"""
Модуль для валидации и геокодирования адресов в Бишкеке
Использует Google Maps Geocoding API для проверки адресов и определения района
"""

import os
import logging
from typing import Optional, Dict
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class AddressInfo:
    """Класс для хранения информации об адресе"""
    original_address: str
    formatted_address: str
    city: str
    district: str  # Район
    street: str
    latitude: float
    longitude: float
    is_valid: bool
    error_message: Optional[str] = None


class KyrgyzstanAddressValidator:
    """Валидатор адресов для Бишкека"""

    # Районы Бишкека
    BISHKEK_DISTRICTS = {
        'Ленинский': ['Ленинский', 'Leninsky', 'Lenin'],
        'Свердловский': ['Свердловский', 'Sverdlovsky', 'Sverdlov'],
        'Первомайский': ['Первомайский', 'Pervomaisky', 'Pervomai'],
        'Октябрьский': ['Октябрьский', 'Oktyabrsky', 'October']
    }

    def __init__(self, google_api_key: Optional[str] = None):
        """
        Инициализация валидатора

        :param google_api_key: API ключ Google Maps (если не указан, берется из env)
        """
        self.api_key = google_api_key or os.getenv('GOOGLE_MAPS_API_KEY')
        self.geocoding_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def validate_address(self, address: str) -> AddressInfo:
        """
        Валидация и геокодирование адреса в Бишкеке

        :param address: Адрес для проверки
        :return: Объект AddressInfo с информацией об адресе
        """
        if not address or len(address.strip()) < 5:
            return AddressInfo(
                original_address=address,
                formatted_address="",
                city="",
                district="",
                street="",
                latitude=0.0,
                longitude=0.0,
                is_valid=False,
                error_message="Адрес слишком короткий"
            )

        # Проверяем, есть ли API ключ
        if not self.api_key:
            logger.warning("Google Maps API key not found. Using basic validation.")
            return self._basic_validation(address)

        try:
            # Геокодирование адреса
            geocode_result = self._geocode_address(address)

            if geocode_result:
                return geocode_result
            else:
                return self._basic_validation(address)

        except Exception as e:
            logger.error(f"Ошибка при валидации адреса: {e}")
            return AddressInfo(
                original_address=address,
                formatted_address="",
                city="",
                district="",
                street="",
                latitude=0.0,
                longitude=0.0,
                is_valid=False,
                error_message=f"Ошибка проверки: {str(e)}"
            )

    def _geocode_address(self, address: str) -> Optional[AddressInfo]:
        """
        Геокодирование адреса через Google Maps API

        :param address: Адрес для геокодирования
        :return: Объект AddressInfo или None
        """
        # Добавляем "Бишкек" к адресу для более точного поиска
        search_address = f"{address}, Бишкек, Кыргызстан" if "Бишкек" not in address else f"{address}, Кыргызстан"

        params = {
            'address': search_address,
            'key': self.api_key,
            'language': 'ru'
        }

        try:
            response = requests.get(self.geocoding_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data['status'] == 'OK' and len(data['results']) > 0:
                result = data['results'][0]

                # Проверяем, что адрес находится в Бишкеке
                if not self._is_in_bishkek(result):
                    return AddressInfo(
                        original_address=address,
                        formatted_address="",
                        city="",
                        district="",
                        street="",
                        latitude=0.0,
                        longitude=0.0,
                        is_valid=False,
                        error_message="Адрес не находится в Бишкеке. Мы доставляем только по Бишкеку."
                    )

                # Извлекаем компоненты адреса
                components = self._parse_address_components(result['address_components'])
                location = result['geometry']['location']

                # Определяем район
                district = self._determine_district(components, location['lat'], location['lng'])

                return AddressInfo(
                    original_address=address,
                    formatted_address=result['formatted_address'],
                    city="Бишкек",
                    district=district,
                    street=components.get('street', ''),
                    latitude=location['lat'],
                    longitude=location['lng'],
                    is_valid=True,
                    error_message=None
                )

            elif data['status'] == 'ZERO_RESULTS':
                return AddressInfo(
                    original_address=address,
                    formatted_address="",
                    city="",
                    district="",
                    street="",
                    latitude=0.0,
                    longitude=0.0,
                    is_valid=False,
                    error_message="Адрес не найден в Бишкеке"
                )
            else:
                logger.warning(f"Google Geocoding API error: {data['status']}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к Google Maps API: {e}")
            return None

    def _is_in_bishkek(self, geocode_result: dict) -> bool:
        """
        Проверка, находится ли адрес в Бишкеке

        :param geocode_result: Результат геокодирования
        :return: True если в Бишкеке
        """
        for component in geocode_result['address_components']:
            types = component['types']
            name = component['long_name']

            # Проверяем, что это Бишкек
            if 'locality' in types or 'administrative_area_level_2' in types:
                if 'Бишкек' in name or 'Bishkek' in name:
                    return True

        return False

    def _parse_address_components(self, components: list) -> Dict[str, str]:
        """
        Парсинг компонентов адреса из ответа Google Maps

        :param components: Компоненты адреса
        :return: Словарь с извлеченными данными
        """
        parsed = {
            'city': 'Бишкек',
            'district': '',
            'street': '',
            'sublocality': ''
        }

        for component in components:
            types = component['types']

            # Район
            if 'sublocality' in types or 'sublocality_level_1' in types:
                parsed['district'] = component['long_name']
            elif 'administrative_area_level_3' in types:
                parsed['sublocality'] = component['long_name']

            # Улица
            elif 'route' in types:
                parsed['street'] = component['long_name']

        return parsed

    def _determine_district(self, components: Dict[str, str], lat: float, lng: float) -> str:
        """
        Определение района Бишкека

        :param components: Компоненты адреса
        :param lat: Широта
        :param lng: Долгота
        :return: Название района
        """
        # Если район уже определен из компонентов
        if components.get('district'):
            return components['district']

        if components.get('sublocality'):
            return components['sublocality']

        # Определяем район по координатам
        return self._get_bishkek_district_by_coords(lat, lng)

    def _get_bishkek_district_by_coords(self, lat: float, lng: float) -> str:
        """
        Определение района Бишкека по координатам

        :param lat: Широта
        :param lng: Долгота
        :return: Название района
        """
        # Примерные границы районов Бишкека
        # Центр Бишкека: примерно 42.87, 74.59

        if lat > 42.88 and lng < 74.59:
            return "Ленинский район"
        elif lat > 42.88 and lng >= 74.59:
            return "Свердловский район"
        elif lat <= 42.88 and lng < 74.59:
            return "Первомайский район"
        elif lat <= 42.88 and lng >= 74.59:
            return "Октябрьский район"

        return "Не определен"

    def _basic_validation(self, address: str) -> AddressInfo:
        """
        Базовая валидация адреса без API (резервный метод)

        :param address: Адрес
        :return: Объект AddressInfo
        """
        # Проверяем наличие слова "Бишкек"
        if 'Бишкек'.lower() not in address.lower() and 'Bishkek'.lower() not in address.lower():
            return AddressInfo(
                original_address=address,
                formatted_address="",
                city="",
                district="",
                street="",
                latitude=0.0,
                longitude=0.0,
                is_valid=False,
                error_message="Укажите адрес в Бишкеке. Мы доставляем только по Бишкеку."
            )

        # Определяем район для Бишкека по ключевым словам
        district = ""
        for district_name, variants in self.BISHKEK_DISTRICTS.items():
            for variant in variants:
                if variant.lower() in address.lower():
                    district = district_name
                    break
            if district:
                break

        is_valid = len(address.strip()) >= 10

        return AddressInfo(
            original_address=address,
            formatted_address=address,
            city="Бишкек",
            district=district or "Не определен",
            street="",
            latitude=0.0,
            longitude=0.0,
            is_valid=is_valid,
            error_message=None if is_valid else "Укажите более подробный адрес"
        )

    def format_address_for_display(self, address_info: AddressInfo) -> str:
        """
        Форматирование адреса для отображения пользователю

        :param address_info: Информация об адресе
        :return: Отформатированная строка
        """
        if not address_info.is_valid:
            return f"❌ Адрес недействителен: {address_info.error_message}"

        parts = []

        if address_info.formatted_address:
            parts.append(f"📍 Адрес: {address_info.formatted_address}")
        else:
            parts.append(f"📍 Адрес: {address_info.original_address}")

        parts.append(f"🏙 Город: Бишкек")

        if address_info.district and address_info.district != "Не определен":
            parts.append(f"📌 Район: {address_info.district}")

        if address_info.latitude and address_info.longitude:
            parts.append(f"🗺 Координаты: {address_info.latitude:.6f}, {address_info.longitude:.6f}")

        return "\n".join(parts)


# Функция для тестирования модуля
async def test_address_validation(address: str, api_key: Optional[str] = None) -> str:
    """
    Тестовая функция для проверки адреса

    :param address: Адрес для проверки
    :param api_key: Google Maps API ключ
    :return: Результат проверки
    """
    validator = KyrgyzstanAddressValidator(api_key)
    result = validator.validate_address(address)

    response = "🔍 Результат проверки адреса:\n\n"
    response += validator.format_address_for_display(result)

    if result.is_valid:
        response += "\n\n✅ Адрес валиден и может быть использован для доставки"
    else:
        response += f"\n\n❌ Проблема с адресом: {result.error_message}"

    return response


# Пример использования для интеграции с ботом
def get_address_validator() -> KyrgyzstanAddressValidator:
    """
    Получить экземпляр валидатора адресов

    :return: Валидатор адресов
    """
    return KyrgyzstanAddressValidator()
