import psycopg2
from prettytable import PrettyTable

conn = psycopg2.connect(
    host='localhost',
    database='scratch',
    user='postgres',
    password='dianaanya'
)
cursor = conn.cursor()

# клиенты
def get_all_clients():
    cursor.execute("SELECT id, full_name, phone, coffee_counter FROM clients ORDER BY id")
    return cursor.fetchall()

def get_client_by_id(client_id):
    cursor.execute("SELECT full_name, phone, coffee_counter FROM clients WHERE id = %s", (client_id,))
    return cursor.fetchone()

def insert_client(full_name, phone):
    cursor.execute("""
        INSERT INTO clients (full_name, phone, coffee_counter)
        VALUES (%s, %s, %s)
    """, (full_name, phone, 1))
    conn.commit()

def update_client_by_id(client_id, full_name, phone, coffee_counter):
    cursor.execute("""
        UPDATE clients 
        SET full_name = %s, phone = %s, coffee_counter = %s
        WHERE id = %s
    """, (full_name, phone, coffee_counter, client_id))
    conn.commit()

def delete_client_by_id(client_id):
    cursor.execute("DELETE FROM clients WHERE id = %s", (client_id,))
    conn.commit()

# сотрудники
def get_all_employees():
    cursor.execute("""
        SELECT e.id, cs.name AS coffee_shop, e.full_name, e.phone, 
               e.hire_date, e.position, e.salary
        FROM employees e
        JOIN coffee_shops cs ON e.coffee_shop_id = cs.id
        ORDER BY e.id
    """)
    return cursor.fetchall()

def get_employee_by_id(employee_id):
    cursor.execute("""
        SELECT e.id, cs.name, e.full_name, e.phone, e.hire_date, e.position, e.salary
        FROM employees e
        JOIN coffee_shops cs ON e.coffee_shop_id = cs.id
        WHERE e.id = %s
    """, (employee_id,))
    return cursor.fetchone()

def insert_employee(coffee_shop_id, full_name, phone, hire_date, position, salary):
    cursor.execute("""
        INSERT INTO employees (coffee_shop_id, full_name, phone, hire_date, position, salary)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (coffee_shop_id, full_name, phone, hire_date, position, salary))
    conn.commit()

def update_employee_by_id(employee_id, coffee_shop_id, full_name, phone, hire_date, position, salary):
    cursor.execute("""
        UPDATE employees 
        SET coffee_shop_id = %s, full_name = %s, phone = %s, 
            hire_date = %s, position = %s, salary = %s
        WHERE id = %s
    """, (coffee_shop_id, full_name, phone, hire_date, position, salary, employee_id))
    conn.commit()

def delete_employee_by_id(employee_id):
    cursor.execute("DELETE FROM employees WHERE id = %s", (employee_id,))
    conn.commit()

def get_all_coffee_shops():
    cursor.execute("SELECT id, name FROM coffee_shops ORDER BY id")
    return cursor.fetchall()

# аналитические запросы
# 1 топ клиентов по сумме покупок
def analytics_top_clients():
    print("\n--- Топ клиентов по сумме покупок ---")
    limit = input("Сколько клиентов показать? (по умолч. 10): ") or "10"

    cursor.execute("""
        SELECT c.full_name, c.phone, 
               COUNT(DISTINCT s.id) AS orders,
               COALESCE(SUM(s.total_amount), 0) AS total_spent
        FROM clients c
        LEFT JOIN sales s ON c.id = s.client_id AND s.status = 'PAID'
        GROUP BY c.id, c.full_name, c.phone
        ORDER BY total_spent DESC
        LIMIT %s
    """, (int(limit),))

    rows = cursor.fetchall()

    table = PrettyTable()
    table.field_names = ["ФИО", "Телефон", "Кол-во заказов", "Потрачено (руб)"]
    for row in rows:
        table.add_row(row)
    print("\n" + str(table))
    input("\nНажмите Enter для продолжения...")

# 2 выручка за период с группировкой по датам
def analytics_revenue_by_period():

    print("\n--- Выручка за период ---")
    start_date = input("Дата начала (ГГГГ-ММ-ДД): ")
    end_date = input("Дата окончания (ГГГГ-ММ-ДД): ")

    cursor.execute("""
        SELECT DATE(sale_datetime) AS sale_date, 
               COUNT(*) AS transactions_count, 
               SUM(total_amount) AS daily_revenue 
        FROM sales 
        WHERE sale_datetime BETWEEN %s AND %s 
          AND status = 'PAID' 
        GROUP BY DATE(sale_datetime) 
        ORDER BY sale_date
    """, (start_date, end_date))

    rows = cursor.fetchall()

    if not rows:
        print("\nЗа указанный период продаж нет")
        input("\nНажмите Enter для продолжения...")
        return

    table = PrettyTable()
    table.field_names = ["Дата", "Кол-во чеков", "Выручка (руб)"]

    total_transactions = 0
    total_revenue = 0

    for row in rows:
        table.add_row(row)
        total_transactions += row[1]
        total_revenue += row[2]

    print("\n" + str(table))
    print(f"\nИТОГО за период: {total_transactions} чеков, {total_revenue:.2f} руб.")
    input("\nНажмите Enter для продолжения...")

# 3 анализ расхождений при инвентаризации на конкретном складе в конкретную дату
def analytics_inventory_discrepancy():
    print("\n--- Расхождения при инвентаризации ---")

    cursor.execute("SELECT id, coffee_shop_id FROM storages ORDER BY id")
    storages = cursor.fetchall()

    print("\nСписок складов:")
    for s in storages:
        print(f"  ID: {s[0]}, Кофейня ID: {s[1]}")

    storage_id = input("\nID склада: ")
    inv_date = input("Дата инвентаризации (ГГГГ-ММ-ДД): ")

    cursor.execute("""
        SELECT i.name, 
               inv.storage_id AS warehouse_id, 
               inv.date_time, 
               inv.theoretical_quantity, 
               inv.factual_quantity, 
               inv.discrepancy 
        FROM inventories inv 
        JOIN ingredients i ON inv.ingredient_id = i.id 
        WHERE DATE(inv.date_time) = %s 
          AND inv.storage_id = %s
        ORDER BY ABS(inv.discrepancy) DESC
    """, (inv_date, storage_id))

    rows = cursor.fetchall()

    if not rows:
        print("\nПо указанному складу и дате инвентаризаций не найдено")
        input("\nНажмите Enter для продолжения...")
        return

    table = PrettyTable()
    table.field_names = ["Ингредиент", "ID склада", "Дата", "Теоретически", "Фактически", "Расхождение"]
    for row in rows:
        table.add_row(row)
    print("\n" + str(table))
    input("\nНажмите Enter для продолжения...")


# 4 средний чек по сотруднику
def analytics_avg_check_by_employee():
    print("\n--- Средний чек по сотруднику ---")

    print("\nВведите полное ФИО сотрудника:")
    full_name = input("ФИО: ").strip()

    if not full_name:
        print("ФИО не может быть пустым")
        input("\nНажмите Enter для продолжения...")
        return

    cursor.execute("""
        SELECT e.id, e.full_name, cs.name AS coffee_shop,
               COUNT(DISTINCT s.id) AS sales_count,
               COALESCE(ROUND(AVG(s.total_amount), 2), 0) AS avg_check,
               COALESCE(SUM(s.total_amount), 0) AS total_revenue,
               MIN(s.total_amount) AS min_check,
               MAX(s.total_amount) AS max_check
        FROM employees e
        JOIN coffee_shops cs ON e.coffee_shop_id = cs.id
        LEFT JOIN sales s ON e.id = s.employee_id AND s.status = 'PAID'
        WHERE e.full_name = %s
        GROUP BY e.id, e.full_name, cs.name
    """, (full_name,))

    row = cursor.fetchone()

    if not row:
        print(f"Сотрудник с ФИО не найден")
        input("\nНажмите Enter для продолжения...")
        return

    if row[3] == 0:
        print(f"У сотрудника {row[1]} нет продаж")
        input("\nНажмите Enter для продолжения...")
        return

    table = PrettyTable()
    table.field_names = ["Показатель", "Значение"]
    table.add_row(["ID сотрудника", row[0]])
    table.add_row(["Сотрудник", row[1]])
    table.add_row(["Кофейня", row[2]])
    table.add_row(["Кол-во продаж", row[3]])
    table.add_row(["Средний чек (руб)", row[4]])
    table.add_row(["Общая выручка (руб)", row[5]])

    print("\n" + str(table))
    input("\nНажмите Enter для продолжения...")

# клиенты
def show_clients():
    rows = get_all_clients()
    table = PrettyTable()
    table.field_names = ["ID", "ФИО", "Телефон", "Бонусы"]
    for row in rows:
        table.add_row(row)
    print("\n" + str(table))
    input("\nНажмите Enter для продолжения...")

def add_client():
    print("\n--- Добавление клиента ---")
    name = input("ФИО: ")
    phone = input("Телефон: ")

    insert_client(name, phone)
    print("Клиент добавлен")
    input("\nНажмите Enter для продолжения...")

def update_client():
    print("\n--- Редактирование клиента ---")
    client_id = input("ID клиента: ")

    client = get_client_by_id(client_id)

    if not client:
        print("Клиент не найден!")
        input("\nНажмите Enter для продолжения...")
        return

    print(f"\nТекущие данные:")
    print(f"  ФИО: {client[0]}")
    print(f"  Телефон: {client[1]}")
    print(f"  Бонусы: {client[2]}")

    print("\nОставьте поле пустым, чтобы не менять")
    name = input(f"Новое ФИО [{client[0]}]: ") or client[0]
    phone = input(f"Новый телефон [{client[1]}]: ") or client[1]
    bonus = input(f"Новые бонусы [{client[2]}]: ") or client[2]

    update_client_by_id(int(client_id), name, phone, int(bonus))
    print("Клиент обновлён")
    input("\nНажмите Enter для продолжения...")

def delete_client():
    print("\n--- Удаление клиента ---")
    client_id = input("ID клиента (0 - отмена): ")

    if client_id == '0':
        print("Операция отменена")
        input("\nНажмите Enter для продолжения...")
        return

    client = get_client_by_id(client_id)

    if not client:
        print("Клиент не найден")
        input("\nНажмите Enter для продолжения...")
        return

    confirm = input(f"Удалить клиента '{client[0]}'? (y/n): ").lower()
    if confirm == 'y':
        delete_client_by_id(int(client_id))
        print("Клиент удалён")
    else:
        print("Операция отменена")

    input("\nНажмите Enter для продолжения...")


def show_employees():
    rows = get_all_employees()
    table = PrettyTable()
    table.field_names = ["ID", "Кофейня", "ФИО", "Телефон", "Дата найма", "Должность", "Зарплата"]
    for row in rows:
        table.add_row(row)
    print("\n" + str(table))
    input("\nНажмите Enter для продолжения...")

def add_employee():
    print("\n--- Добавление сотрудника ---")

    shops = get_all_coffee_shops()
    print("\nСписок кофеен:")
    for shop in shops:
        print(f"  {shop[0]}. {shop[1]}")

    coffee_shop_id = input("\nID кофейни: ")
    full_name = input("ФИО: ")
    phone = input("Телефон: ")
    hire_date = input("Дата найма (ГГГГ-ММ-ДД): ")
    position = input("Должность: ")
    salary = input("Зарплата: ")

    insert_employee(int(coffee_shop_id), full_name, phone, hire_date, position, float(salary))
    print("Сотрудник добавлен")
    input("\nНажмите Enter для продолжения...")

def update_employee():
    print("\n--- Редактирование сотрудника ---")
    employee_id = input("ID сотрудника: ")

    employee = get_employee_by_id(employee_id)

    if not employee:
        print("Сотрудник не найден")
        input("\nНажмите Enter для продолжения...")
        return

    print(f"\nТекущие данные:")
    print(f"  Кофейня: {employee[1]}")
    print(f"  ФИО: {employee[2]}")
    print(f"  Телефон: {employee[3]}")
    print(f"  Дата найма: {employee[4]}")
    print(f"  Должность: {employee[5]}")
    print(f"  Зарплата: {employee[6]}")

    shops = get_all_coffee_shops()
    print("\nСписок кофеен:")
    for shop in shops:
        print(f"  {shop[0]}. {shop[1]}")

    print("\nОставьте поле пустым, чтобы не менять")
    coffee_shop_id = input(f"ID кофейни [{employee[1]}]: ") or employee[0]
    full_name = input(f"Новое ФИО [{employee[2]}]: ") or employee[2]
    phone = input(f"Новый телефон [{employee[3]}]: ") or employee[3]
    hire_date = input(f"Новая дата найма [{employee[4]}]: ") or employee[4]
    position = input(f"Новая должность [{employee[5]}]: ") or employee[5]
    salary = input(f"Новая зарплата [{employee[6]}]: ") or employee[6]

    update_employee_by_id(int(employee_id), int(coffee_shop_id), full_name, phone,
                          hire_date, position, float(salary))
    print("Сотрудник обновлён")
    input("\nНажмите Enter для продолжения...")

def delete_employee():
    print("\n--- Удаление сотрудника ---")
    employee_id = input("ID сотрудника (0 - отмена): ")

    if employee_id == '0':
        print("Операция отменена")
        input("\nНажмите Enter для продолжения...")
        return

    employee = get_employee_by_id(employee_id)

    if not employee:
        print("Сотрудник не найден")
        input("\nНажмите Enter для продолжения...")
        return

    confirm = input(f"Удалить сотрудника '{employee[2]}'? (y/n): ").lower()
    if confirm == 'y':
        delete_employee_by_id(int(employee_id))
        print("Сотрудник удалён")
    else:
        print("Операция отменена")

    input("\nНажмите Enter для продолжения...")


def show_menu():
    print("""
==================================================
COFFEE SHOPS
==================================================
--- Работа с клиентами ---
1. Показать всех клиентов
2. Добавить клиента
3. Редактировать клиента
4. Удалить клиента

--- Работа с сотрудниками ---
5. Показать всех сотрудников
6. Добавить сотрудника
7. Редактировать сотрудника
8. Удалить сотрудника

--- Аналитика ---
9. Топ клиентов по сумме покупок
10. Выручка за период
11. Расхождения при инвентаризации
12. Средний чек по сотрудникам

0. Выход
--------------------------------------------------
    """)

def main():
    show_menu()
    choice = input("Выберите действие: ")

    if choice == '1':
        show_clients()
    elif choice == '2':
        add_client()
    elif choice == '3':
        update_client()
    elif choice == '4':
        delete_client()
    elif choice == '5':
        show_employees()
    elif choice == '6':
        add_employee()
    elif choice == '7':
        update_employee()
    elif choice == '8':
        delete_employee()
    elif choice == '9':
        analytics_top_clients()
    elif choice == '10':
        analytics_revenue_by_period()
    elif choice == '11':
        analytics_inventory_discrepancy()
    elif choice == '12':
        analytics_avg_check_by_employee()
    elif choice == '0':
        print("\nЗавершение работы...")
        cursor.close()
        conn.close()
        return
    else:
        print("Неверный номер команды!")
        input("\nНажмите Enter для продолжения...")
    main()

if __name__ == "__main__":
    main()