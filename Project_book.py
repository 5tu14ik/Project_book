import sqlite3
from pathlib import Path


class Library:
    def __init__(self):
        db = Path.home() / 'Desktop' / 'library_data' / 'library.db'
        db.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db))
        self.c = self.conn.cursor()
        self.c.execute("PRAGMA foreign_keys = ON;")

        self.c.execute('''CREATE TABLE IF NOT EXISTS authors (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, birth_year INTEGER)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, 
            author_id INTEGER NOT NULL, year INTEGER, genre TEXT,
            FOREIGN KEY (author_id) REFERENCES authors(id) ON DELETE CASCADE)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT, book_id INTEGER NOT NULL,
            reader_id INTEGER NOT NULL, loan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            return_date TIMESTAMP, is_returned BOOLEAN DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE)''')
        self.conn.commit()
        print(f"{db}")

    def close(self):
        self.conn.close()

    def add_book(self, title, author, birth_year=None, year=None, genre=None):
        try:
            self.c.execute("BEGIN")
            self.c.execute("SELECT id FROM authors WHERE name=?", (author,))
            r = self.c.fetchone()
            if r:
                aid = r[0]
            else:
                self.c.execute("INSERT INTO authors (name, birth_year) VALUES (?,?)", (author, birth_year))
                aid = self.c.lastrowid
                print(f"Новый автор: {author}")
            self.c.execute("INSERT INTO books (title, author_id, year, genre) VALUES (?,?,?,?)",
                           (title, aid, year, genre))
            self.conn.commit()
            print(f"Книга '{title}' добавлена!")
        except Exception as e:
            self.conn.rollback()
            print(f"{e}")

    def delete_book(self, book_id):
        self.c.execute("SELECT title FROM books WHERE id=?", (book_id,))
        book = self.c.fetchone()
        if not book:
            print("Книга не найдена")
            return
        self.c.execute("SELECT COUNT(*) FROM loans WHERE book_id=? AND is_returned=0", (book_id,))
        if self.c.fetchone()[0] > 0:
            print(f"Книга '{book[0]}' выдана")
            return
        self.c.execute("DELETE FROM books WHERE id=?", (book_id,))
        self.conn.commit()
        print(f"Книга '{book[0]}' удалена")

    def delete_author(self, author_id):
        self.c.execute("SELECT name FROM authors WHERE id=?", (author_id,))
        author = self.c.fetchone()
        if not author:
            print("Автор не найден")
            return
        self.c.execute("DELETE FROM authors WHERE id=?", (author_id,))
        self.conn.commit()
        print(f"Автор '{author[0]}' удален")

    def edit_book(self, book_id, **kwargs):
        self.c.execute("SELECT title FROM books WHERE id=?", (book_id,))
        book = self.c.fetchone()
        if not book:
            print("Книга не найдена")
            return
        fields = {'title': 'title', 'year': 'year', 'genre': 'genre'}
        updates = [f"{fields[k]} = ?" for k in kwargs if k in fields and kwargs[k] is not None]
        if not updates:
            print("Нет изменений")
            return
        params = [kwargs[k] for k in fields if k in kwargs and kwargs[k] is not None] + [book_id]
        self.c.execute(f"UPDATE books SET {', '.join(updates)} WHERE id=?", params)
        self.conn.commit()
        print(f"Книга '{book[0]}' обновлена")

    def get_books(self):
        self.c.execute('''SELECT b.id, b.title, a.name, b.year, b.genre 
                         FROM books b JOIN authors a ON b.author_id = a.id ORDER BY b.id''')
        rows = self.c.fetchall()
        print("\n" + "=" * 80 + "\nВСЕ КНИГИ:\n" + "=" * 80)
        if not rows:
            print("  Пусто")
            return
        for r in rows:
            print(f"ID: {r[0]:2} | {r[1][:30]:30} | {r[2][:20]:20} | {r[3]} | {r[4]}")
        print("=" * 80)

    def search(self, q):
        self.c.execute('''SELECT b.id, b.title, a.name, b.year, b.genre FROM books b 
                         JOIN authors a ON b.author_id = a.id 
                         WHERE b.title LIKE ? OR a.name LIKE ?''', (f'%{q}%', f'%{q}%'))
        rows = self.c.fetchall()
        print(f"\nПОИСК: '{q}'\n" + "-" * 70)
        if not rows:
            print("  Ничего не найдено")
            return
        for r in rows:
            print(f"ID: {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]}")

    def open_folder(self):
        import subprocess, platform, os
        folder = Path.home() / 'Desktop' / 'library_data'
        if platform.system() == 'Windows':
            os.startfile(str(folder))
        elif platform.system() == 'Darwin':
            subprocess.run(['open', str(folder)])
        else:
            subprocess.run(['xdg-open', str(folder)])


def main():
    lib = Library()
    menu = {
        '1': ('Все книги', lib.get_books),
        '2': ('Добавить книгу', lambda: lib.add_book(
            input("Название: ").strip(),
            input("Автор: ").strip(),
            input("Год рождения (enter - пропустить): ").strip() or None,
            input("Год издания: ").strip() or None,
            input("Жанр: ").strip() or None
        )),
        '3': ('Удалить книгу',
              lambda: lib.delete_book(int(input("ID: ").strip())) if input("ID: ").strip().isdigit() else print(
                  "Неверный ID")),
        '4': ('Редактировать книгу', lambda: lib.edit_book(
            int(input("ID: ").strip()),
            title=input("Новое название (enter - пропустить): ").strip() or None,
            year=input("Новый год (enter - пропустить): ").strip() or None,
            genre=input("Новый жанр (enter - пропустить): ").strip() or None
        ) if input("ID: ").strip().isdigit() else print("Неверный ID")),
        '5': ('Удалить автора', lambda: lib.delete_author(int(input("ID автора: ").strip())) if input(
            "ID автора: ").strip().isdigit() else print("Неверный ID")),
        '6': ('Поиск', lambda: lib.search(input("Что ищем: ").strip())),
        '7': ('Открыть папку', lib.open_folder),
    }

    while True:
        print("\n" + "=" * 50 + "\nБИБЛИОТЕКА\n" + "=" * 50)
        for k, (name, _) in menu.items():
            print(f"{k}. {name}")
        print("0. Выход\n" + "=" * 50)

        choice = input("Выберите: ").strip()
        if choice == '0':
            print("До свидания")
            break
        if choice in menu:
            menu[choice][1]()
        else:
            print("Ошибка")

    lib.close()


if __name__ == "__main__":
    main()