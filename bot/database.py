import sqlite3
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        """Создание необходимых таблиц, если они не существуют"""
        # Таблица пользователей с расписанием обедов
        self.cursor.execute('''
              CREATE TABLE IF NOT EXISTS lunch_schedule (
                  user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  lunch_time TEXT,
                  notifications_enabled INTEGER DEFAULT 1
              )
          ''')
        try:
            self.cursor.execute('ALTER TABLE lunch_schedule ADD COLUMN notifications_enabled INTEGER DEFAULT 1')
            self.connection.commit()
        except sqlite3.OperationalError:
            pass

        # Таблица для хранения информации о закрепленном сообщении
        self.cursor.execute('''
              CREATE TABLE IF NOT EXISTS pinned_messages (
                  id INTEGER PRIMARY KEY,
                  message_id INTEGER,
                  date TEXT
              )
          ''')

        self.connection.commit()

    def set_lunch_time(self, user_id, username, first_name, last_name, lunch_time):
        """Установка времени обеда для пользователя с сохранением настроек уведомлений"""
        try:
            # Получаем текущие настройки уведомлений
            self.cursor.execute(
                'SELECT notifications_enabled FROM lunch_schedule WHERE user_id = ?',
                (user_id,)
            )
            current_notifications = self.cursor.fetchone()  # ✅ ДОБАВИТЬ .fetchone()

            # Если пользователь уже существует, сохраняем его настройки уведомлений
            notifications_enabled = current_notifications[0] if current_notifications else 1

            self.cursor.execute('''
                  INSERT OR REPLACE INTO lunch_schedule 
                  (user_id, username, first_name, last_name, lunch_time, notifications_enabled) 
                  VALUES (?, ?, ?, ?, ?, ?)
              ''', (user_id, username, first_name, last_name, lunch_time, notifications_enabled))
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при установке времени обеда для пользователя {user_id}: {e}")
            return False

    def get_lunch_time(self, user_id):
        """Получение времени обеда пользователя"""
        self.cursor.execute('SELECT lunch_time FROM lunch_schedule WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_users_by_lunch_time(self, lunch_time):
        """Получение всех пользователей с определенным временем обеда"""
        self.cursor.execute('''
              SELECT user_id, username, first_name, last_name 
              FROM lunch_schedule 
              WHERE lunch_time = ?
          ''', (lunch_time,))
        return self.cursor.fetchall()

    def get_all_lunch_schedules(self):
        """Получение всех расписаний обедов"""
        self.cursor.execute('''
              SELECT user_id, username, first_name, last_name, lunch_time 
              FROM lunch_schedule 
              ORDER BY lunch_time
          ''')
        return self.cursor.fetchall()

    def delete_lunch_time(self, user_id):
        """Удаление времени обеда для пользователя"""
        with self.connection:
            self.cursor.execute("DELETE FROM lunch_schedule WHERE user_id = ?", (user_id,))
            return True

    def set_pinned_message(self, message_id, date):
        """Сохранение информации о закрепленном сообщении"""
        self.cursor.execute('''
              INSERT OR REPLACE INTO pinned_messages (id, message_id, date) 
              VALUES (1, ?, ?)
          ''', (message_id, date))
        self.connection.commit()

    def get_pinned_message(self):
        """Получение информации о закрепленном сообщении"""
        self.cursor.execute('SELECT message_id, date FROM pinned_messages WHERE id = 1')
        result = self.cursor.fetchone()
        return result if result else None

    def get_user_lunch_time_with_notifications(self, user_id):
        """Получить время обеда и статус уведомлений для пользователя"""
        try:
            self.cursor.execute(
                "SELECT lunch_time, notifications_enabled FROM lunch_schedule WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            if result:
                return result[0], bool(result[1])  # Возвращаем lunch_time, notifications_enabled
            else:
                return None, True  # По умолчанию уведомления включены
        except Exception as e:
            logging.error(f"Ошибка при получении данных пользователя {user_id}: {e}")
            return None, True

    def toggle_notifications(self, user_id):
        """Переключить статус уведомлений для пользователя"""
        try:
            # Получаем текущий статус
            current_status = self.cursor.execute(
                'SELECT notifications_enabled FROM lunch_schedule WHERE user_id = ?',
                (user_id,)
            ).fetchone()

            if current_status is None:
                return False

            # Переключаем статус
            new_status = 0 if current_status[0] else 1
            self.cursor.execute(
                'UPDATE lunch_schedule SET notifications_enabled = ? WHERE user_id = ?',
                (new_status, user_id)
            )
            self.connection.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка при переключении уведомлений: {e}")
            return False

    def remove_user_from_schedule(self, user_id):
        """Удалить пользователя из расписания"""
        try:
            self.cursor.execute('DELETE FROM lunch_schedule WHERE user_id = ?', (user_id,))
            self.connection.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            logging.error(f"Ошибка при удалении пользователя: {e}")
            return False

    def get_users_by_lunch_time_with_notifications(self, lunch_time):
        """Получить пользователей по времени обеда с учетом включенных уведомлений"""
        self.cursor.execute(
            'SELECT user_id, username, first_name, last_name FROM lunch_schedule WHERE lunch_time = ? AND notifications_enabled = 1',
            (lunch_time,)
        )
        return self.cursor.fetchall()

    def clear_pinned_message(self):
        """Очистка информации о закрепленном сообщении"""
        self.cursor.execute('DELETE FROM pinned_messages WHERE id = 1')
        self.connection.commit()

    def close(self):
        """Закрытие соединения с базой данных"""
        self.connection.close()