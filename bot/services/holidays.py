import holidays
from datetime import datetime, date

class WorkdayChecker:
    def __init__(self):
        # Российские праздники
        self.ru_holidays = holidays.Russia()

    def is_workday(self, check_date=None):
        """
        Проверяет, является ли день рабочим
        Args:
            check_date: дата для проверки (по умолчанию сегодня)
        Returns:
            bool: True если рабочий день, False если выходной/праздник
        """
        if check_date is None:
            check_date = date.today()
        elif isinstance(check_date, datetime):
            check_date = check_date.date()

        # Проверяем выходные (суббота=5, воскресенье=6)
        if check_date.weekday() >= 5:
            return False

        # Проверяем праздники
        if check_date in self.ru_holidays:
            return False

        return True

    def get_holiday_name(self, check_date=None):
        """
        Возвращает название праздника, если день праздничный
        """
        if check_date is None:
            check_date = date.today()
        elif isinstance(check_date, datetime):
            check_date = check_date.date()

        return self.ru_holidays.get(check_date)

    def get_next_workday(self, start_date=None):
        """
        Возвращает следующий рабочий день
        """
        if start_date is None:
            start_date = date.today()
        elif isinstance(start_date, datetime):
            start_date = start_date.date()

        current_date = start_date + timedelta(days=1)
        while not self.is_workday(current_date):
            current_date += timedelta(days=1)

        return current_date