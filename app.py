from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QPushButton, QLineEdit, QDialog, QScrollArea, QComboBox, QTableWidget, QTableWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtSql import QSqlDatabase, QSqlQuery
from PySide6.QtGui import QFont, QIntValidator, QIcon, QPixmap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
import sys

class PartnerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Мастер пол")
        self.setWindowIcon(QIcon('icon.ico'))
        self.resize(800, 600)

        # Подключение к базе данных
        self.db = QSqlDatabase.addDatabase("QSQLITE")
        self.db.setDatabaseName("database.db")
        if not self.db.open():
            self.show_error_message("Ошибка подключения", "Не удалось подключиться к базе данных.")
            sys.exit(1)

        # Основной виджет и макет
        self.selected_card = None
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_widget.setStyleSheet("background-color: white; color: black;")  # Черный текст по умолчанию
        self.setCentralWidget(main_widget)

        # Верхний лэйаут с кнопками "История" и "Партнеры"
        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        self.header.setStyleSheet("background-color: #F4E8D3; padding: 10px;")
        main_layout.addWidget(self.header)

        logo_label = QLabel()
        logo_pixmap = QPixmap('logotype.png')
        logo_pixmap = logo_pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio)
        logo_label.setPixmap(logo_pixmap)
        header_layout.addWidget(logo_label)

        app_title = QLabel("Мастер пол")
        app_title.setStyleSheet("font-size: 20px; font-weight: bold; color: black;")
        header_layout.addWidget(app_title)

        # Кнопка "История" с ее стилем и макетом
        self.history_widget = QWidget()
        self.history_widget.setStyleSheet("background-color: #67BA80; border-radius: 5px; padding: 5px;")
        history_layout = QHBoxLayout(self.history_widget)
        
        self.history_button = QPushButton("История")
        self.history_button.setStyleSheet("background-color: transparent; color: white; padding: 10px;")
        self.history_button.clicked.connect(self.show_history)
        history_layout.addWidget(self.history_button)
        header_layout.addWidget(self.history_widget)

        # Виджет для кнопок "Партнеры" и "+"
        self.partners_widget = QWidget()
        self.partners_widget.setStyleSheet("background-color: #67BA80; border-radius: 5px; padding: 5px;")
        partners_layout = QHBoxLayout(self.partners_widget)

        # Кнопка "Партнеры"
        self.partners_button = QPushButton("Партнеры")
        self.partners_button.setStyleSheet("background-color: transparent; color: white; padding: 10px;")
        self.partners_button.clicked.connect(self.show_partner_list)

        # Кнопка "+"
        self.add_button = QPushButton("+")
        self.add_button.setStyleSheet("background-color: transparent; color: white; padding: 10px;")
        self.add_button.clicked.connect(self.open_add_partner_dialog)

        partners_layout.addWidget(self.partners_button)
        partners_layout.addWidget(self.add_button)
        header_layout.addWidget(self.partners_widget)

        # Прокручиваемая область для списка партнеров
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        main_layout.addWidget(self.scroll_area)

        # Загрузка данных
        self.show_partner_list()
        
    def show_error_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()

    def open_add_partner_dialog(self):
        dialog = PartnerDialog(self)
        dialog.setStyleSheet(dialog.get_add_partner_dialog_style())
        dialog.exec()
        self.load_partners()

    def show_history(self):
        # Очистка основной области
        self.scroll_area.takeWidget()
        history_widget = QWidget()
        layout = QVBoxLayout(history_widget)

        # Таблица для отображения истории партнеров
        self.history_table = QTableWidget()
        layout.addWidget(self.history_table)
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Тип продукции", "Название продукта", "Партнер", "Количество", "Дата продажи"])
        self.history_table.setStyleSheet("color: black;")

        # Кнопка "Отчет"
        self.report_button = QPushButton("Отчет")
        self.report_button.setStyleSheet("background-color: #67BA80; color: white; padding: 10px;")
        self.report_button.clicked.connect(self.generate_report)
        layout.addWidget(self.report_button)

        # Загрузка данных в таблицу
        self.load_history_data()
        self.scroll_area.setWidget(history_widget)

    def load_history_data(self):
        query = QSqlQuery("SELECT pt.product_type, pd.product_name, p.partner_name, pp.quantity, pp.sale_date, "
                          "pt.coefficient, mt.defect_rate, pd.product_id, pp.quantity "
                          "FROM Partner_Products pp "
                          "JOIN Product_Details pd ON pp.product_name = pd.product_id "
                          "JOIN Partners p ON pp.partner_name = p.partner_id "
                          "JOIN Product_Types pt ON pd.product_type = pt.type_id "
                          "JOIN Material_Types mt ON mt.material_type_id = 1")  # Используем material_type_id = 1 для всех записей

        self.history_table.setRowCount(0)
        while query.next():
            rows = self.history_table.rowCount()
            self.history_table.insertRow(rows)

            product_type = query.value(0)
            product_name = query.value(1)
            partner_name = query.value(2)
            sale_date = query.value(4)
            coefficient = query.value(5)
            defect_rate = query.value(6)

            # Расчет количества материала
            calculated_quantity = self.calculate_material(coefficient, defect_rate, query.value(8), 1.0, 1.0)  # Используем параметры по умолчанию

            self.history_table.setItem(rows, 0, QTableWidgetItem(str(product_type)))
            self.history_table.setItem(rows, 1, QTableWidgetItem(str(product_name)))
            self.history_table.setItem(rows, 2, QTableWidgetItem(str(partner_name)))
            self.history_table.setItem(rows, 3, QTableWidgetItem(str(calculated_quantity)))
            self.history_table.setItem(rows, 4, QTableWidgetItem(str(sale_date)))

    def generate_report(self):
        try:
            c = canvas.Canvas("report.pdf", pagesize=A4)
            pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))  # Используем шрифт с поддержкой кириллицы
            c.setFont("DejaVuSans", 14)

            c.drawString(200, 800, "Отчет по продажам")
            y = 750
            c.setFont("DejaVuSans", 9)
            i = 1
            for row in range(self.history_table.rowCount()):
                row_data = [self.history_table.item(row, col).text() for col in range(5)]
                c.drawString(10, y, f"{i})")
                c.drawString(20, y, " | ".join(row_data))
                y -= 20
                i += 1
            c.save()
        except Exception as e:
            self.show_error_message("Ошибка генерации отчета", f"Не удалось создать отчет. Ошибка: {str(e)}")

    def show_partner_list(self):
        # Очистка основной области
        self.scroll_area.takeWidget()
        partners_widget = QWidget()
        layout = QVBoxLayout(partners_widget)

        # Загрузка партнеров
        self.partner_list_layout = QVBoxLayout()
        layout.addLayout(self.partner_list_layout)

        # Загрузка данных
        self.load_partners()
        self.scroll_area.setWidget(partners_widget)
        
    def calculate_discount(self, total_sales):
        if total_sales >= 300000:
            return "15%"
        elif total_sales >= 50000:
            return "10%"
        elif total_sales >= 10000:
            return "5%"
        else:
            return "0%"

    def load_partners(self):
        # Очистка текущего списка партнеров
        while self.partner_list_layout.count():
            child = self.partner_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Запрос для получения данных партнеров из базы
        query = QSqlQuery("SELECT partner_id, partner_type, partner_name, director_name, phone, rating FROM Partners")
        while query.next():
            partner_id = query.value(0)
            partner_type = query.value(1)
            partner_name = query.value(2)
            director_name = query.value(3)
            phone = query.value(4)
            rating = query.value(5)

            # Подсчет общего объема продаж для расчета скидки
            sales_query = QSqlQuery()
            sales_query.prepare("SELECT SUM(quantity) FROM Partner_Products WHERE partner_name = ?")
            sales_query.addBindValue(partner_id)
            sales_query.exec()
            sales_query.next()
            total_sales = sales_query.value(0) if sales_query.value(0) else 0
            discount = self.calculate_discount(total_sales)

            # Создание карточки для каждого партнера
            partner_card = QFrame()
            partner_card.setStyleSheet(""" 
                    background-color: #FFFFFF;
                    border: 1px solid black;
                    border-radius: 10px;
                    padding: 1px;
            """)
            
            # Сохранение исходного стиля
            original_style = partner_card.styleSheet()

            # Обработчик для однократного клика
            def on_single_click(event, card=partner_card, orig_style=original_style):
                # Проверка, есть ли ранее выделенная карточка и сброс её цвета
                if self.selected_card and self.selected_card != card:
                    self.selected_card.setStyleSheet(orig_style)
                # Выделение текущей карточки и установка зеленого фона
                card.setStyleSheet("background-color: #67BA80; border: 1px solid black; border-radius: 10px; padding: 1px;")
                # Обновление ссылки на текущую выбранную карточку
                self.selected_card = card
            
            # Присваиваем обработчики событиям клика
            partner_card.mousePressEvent = on_single_click  # Одинарный клик изменяет цвет
            partner_card.mouseDoubleClickEvent = lambda event, pid=partner_id, pt=partner_type, pn=partner_name, dn=director_name, ph=phone, rt=rating: self.open_edit_partner_dialog(pid, pt, pn, dn, ph, rt)

            # Настройка лэйаутов карточки
            partner_card_layout = QHBoxLayout()
            left_layout = QVBoxLayout()

            name_label = QLabel(f"{partner_type} | {partner_name}")
            name_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            name_label.setStyleSheet("color: black;border: 0px;")
            
            director_label = QLabel(f"Директор: {director_name}")
            phone_label = QLabel(f"Телефон: {phone}")
            rating_label = QLabel(f"Рейтинг: {rating}")

            for label in (director_label, phone_label, rating_label):
                label.setFont(QFont("Segoe UI", 10))
                label.setStyleSheet("color: black;border: 0px;")
            
            # Настройка и добавление скидки
            discount_label = QLabel(discount)
            discount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            discount_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
            discount_label.setStyleSheet("color: black;border: 0px;")  # Черный текст скидки

            left_layout.addWidget(name_label)
            left_layout.addWidget(director_label)
            left_layout.addWidget(phone_label)
            left_layout.addWidget(rating_label)
            
            partner_card_layout.addLayout(left_layout)
            partner_card_layout.addWidget(discount_label)
            partner_card.setLayout(partner_card_layout)

            # Добавление карточки в общий список
            self.partner_list_layout.addWidget(partner_card)

    def delete_partner(self):
        if self.partner_id is not None:
            query = QSqlQuery()
            query.prepare("DELETE FROM Partners WHERE partner_id = ?")
            query.addBindValue(self.partner_id)
            try:
                if not query.exec():
                    raise Exception(query.lastError().text())
                # Обнуляем выбранную карточку после удаления
                if self.selected_card:
                    self.selected_card = None
            except Exception as e:
                self.show_error_message("Ошибка удаления", f"Не удалось удалить партнера. Ошибка: {str(e)}")
        self.load_partners()  # Обновляем список партнеров после удаления


    
    def open_edit_partner_dialog(self, partner_id, partner_type, partner_name, director_name, phone, rating):
        dialog = PartnerDialog(self, partner_id, partner_type, partner_name, director_name, phone, rating)
        dialog.setStyleSheet(dialog.get_edit_partner_dialog_style())
        dialog.exec()
        self.load_partners()  # Обновляем список партнеров после редактирования

    def calculate_material(self, coefficient, defect_rate, product_quantity, param1, param2):
        required_material = product_quantity * param1 * param2 * coefficient
        required_material_with_defect = required_material * (1 + defect_rate)
        return int(required_material_with_defect)
    
class PartnerDialog(QDialog):
    def __init__(self, parent=None, partner_id=None, partner_type='', partner_name='', director_name='', phone='', rating=0):
        super().__init__(parent)
        self.partner_id = partner_id  # ID партнера для удаления или редактирования
        self.setWindowTitle("Добавление партнера")
        self.setFixedSize(600, 400)

        layout = QVBoxLayout()

        # Поля формы
        self.name_edit = QLineEdit(partner_name)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["ЗАО", "ООО", "ОАО","ПАО"])
        self.type_combo.setCurrentText(partner_type)
        self.director_edit = QLineEdit(director_name)
        self.phone_edit = QLineEdit(phone)
        self.rating_edit = QLineEdit(str(rating))
        self.rating_edit.setValidator(QIntValidator(0, 100))

        layout.addWidget(QLabel("Наименование партнера"))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel("Тип партнера"))
        layout.addWidget(self.type_combo)
        layout.addWidget(QLabel("ФИО Директора"))
        layout.addWidget(self.director_edit)
        layout.addWidget(QLabel("Телефон"))
        layout.addWidget(self.phone_edit)
        layout.addWidget(QLabel("Рейтинг"))
        layout.addWidget(self.rating_edit)

        # Кнопка сохранения
        self.save_button = QPushButton("Сохранить")
        self.save_button.setFixedHeight(30)
        self.save_button.setFont(QFont("Segoe UI", 10))
        self.save_button.setStyleSheet("""
            background-color: #67BA80;
            color: black;  /* Черный текст на кнопке */
            border-radius: 5px;
            padding: 5px;
        """)
        self.save_button.clicked.connect(self.save_partner)
        layout.addWidget(self.save_button)

        # Кнопка удаления (отображается только при редактировании)
        if self.partner_id is not None:
            self.setWindowTitle("Редактирование партнера")
            self.delete_button = QPushButton("Удалить")
            self.delete_button.setFixedHeight(30)
            self.delete_button.setFont(QFont("Segoe UI", 10))
            self.delete_button.setStyleSheet("""
                background-color: #FF6B6B;
                color: black;  /* Черный текст на кнопке */
                border-radius: 5px;
                padding: 5px;
            """)
            self.delete_button.clicked.connect(self.delete_partner)
            layout.addWidget(self.delete_button)

        self.setLayout(layout)
        
        
    def get_add_partner_dialog_style(self):
        # Стиль для окна добавления партнера
        return """
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                font-size: 12pt;
                font-weight: bold;
                color: black;
            }
            QLineEdit, QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #67BA80;
                border-radius: 5px;
                padding: 5px;
                font-size: 10pt;
                color: black;
            }
            QPushButton {
                background-color: #67BA80;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #558C60;
            }
        """

    def get_edit_partner_dialog_style(self):
        # Стиль для окна редактирования партнера (можно сделать слегка отличающимся)
        return """
            QDialog {
                background-color: #FFFFFF;
            }
            QLabel {
                font-size: 12pt;
                font-weight: bold;
                color: black;
            }
            QLineEdit, QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #67BA80;
                border-radius: 5px;
                padding: 5px;
                font-size: 10pt;
                color: black;
            }
            QPushButton {
                background-color: #67BA80;
                color: white;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #558C60;
            }
            QPushButton#delete_button {
                background-color: #FF6B6B;
                color: black;
            }
            QPushButton#delete_button:hover {
                background-color: #D9534F;
            }
        """

    def save_partner(self):
        name = self.name_edit.text()
        partner_type = self.type_combo.currentText()
        director = self.director_edit.text()
        phone = self.phone_edit.text()
        rating = int(self.rating_edit.text()) if self.rating_edit.text().isdigit() else 0

        # Проверка на пустые значения
        if not all([name, partner_type, director, phone]):
            self.show_error_message("Ошибка", "Все поля должны быть заполнены.")
            return

        query = QSqlQuery()
        if self.partner_id is None:
            query.prepare("INSERT INTO Partners (partner_name, partner_type, director_name, phone, rating) VALUES (?, ?, ?, ?, ?)")
        else:
            query.prepare("UPDATE Partners SET partner_name = ?, partner_type = ?, director_name = ?, phone = ?, rating = ? WHERE partner_id = ?")

        # Привязка значений к запросу
        query.addBindValue(name)
        query.addBindValue(partner_type)
        query.addBindValue(director)
        query.addBindValue(phone)
        query.addBindValue(rating)

        if self.partner_id is not None:
            query.addBindValue(self.partner_id)

        # Выполнение запроса
        try:
            if not query.exec():
                raise Exception(query.lastError().text())
            self.accept()
        except Exception as e:
            self.show_error_message("Ошибка сохранения", f"Не удалось сохранить партнера. Ошибка: {str(e)}")

    def delete_partner(self):
        if self.partner_id is not None:
            query = QSqlQuery()
            query.prepare("DELETE FROM Partners WHERE partner_id = ?")
            query.addBindValue(self.partner_id)
            try:
                if not query.exec():
                    raise Exception(query.lastError().text())
            except Exception as e:
                self.show_error_message("Ошибка удаления", f"Не удалось удалить партнера. Ошибка: {str(e)}")
        self.accept()

    def show_error_message(self, title, message):
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle(title)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec()


# Создание приложения
app = QApplication(sys.argv)
window = PartnerApp()
window.show()
sys.exit(app.exec())


