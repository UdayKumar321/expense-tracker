"""
Personal Expense Tracker
Python mini project: Tkinter (UI) + SQLite (database) + CSV export.
Run:  python expense_tracker.py
"""
import csv
import sqlite3
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

DB_FILE = "expenses.db"
CATEGORIES = ["Food", "Travel", "Shopping", "Bills", "Health", "Entertainment", "Other"]


# ---------------------------------------------------------------- database
class Database:
    def __init__(self, path=DB_FILE):
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS expenses (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   date TEXT NOT NULL,
                   category TEXT NOT NULL,
                   amount REAL NOT NULL,
                   note TEXT
               )"""
        )
        self.conn.commit()

    def add(self, d, category, amount, note):
        self.conn.execute(
            "INSERT INTO expenses (date, category, amount, note) VALUES (?, ?, ?, ?)",
            (d, category, amount, note),
        )
        self.conn.commit()

    def delete(self, expense_id):
        self.conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        self.conn.commit()

    def fetch(self, month=None):
        """month is 'YYYY-MM' or None for all records."""
        if month:
            cur = self.conn.execute(
                "SELECT id, date, category, amount, note FROM expenses "
                "WHERE date LIKE ? ORDER BY date DESC, id DESC",
                (month + "%",),
            )
        else:
            cur = self.conn.execute(
                "SELECT id, date, category, amount, note FROM expenses "
                "ORDER BY date DESC, id DESC"
            )
        return cur.fetchall()

    def totals_by_category(self, month=None):
        rows = self.fetch(month)
        totals = {}
        for _, _, cat, amt, _ in rows:
            totals[cat] = totals.get(cat, 0) + amt
        return totals


def validate(d, amount_text):
    """Return (clean_date, amount) or raise ValueError with a readable message."""
    try:
        clean_date = datetime.strptime(d.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        raise ValueError("Date must be in YYYY-MM-DD format.")
    try:
        amount = float(amount_text)
    except ValueError:
        raise ValueError("Amount must be a number.")
    if amount <= 0:
        raise ValueError("Amount must be greater than zero.")
    return clean_date, round(amount, 2)


# ---------------------------------------------------------------------- UI
class ExpenseApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Personal Expense Tracker")
        self.geometry("820x640")
        self.db = Database()
        self._build_form()
        self._build_table()
        self._build_summary()
        self.refresh()

    # ----- layout
    def _build_form(self):
        frame = ttk.LabelFrame(self, text="Add Expense")
        frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(frame, text="Date").grid(row=0, column=0, padx=5, pady=5)
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(frame, textvariable=self.date_var, width=12).grid(row=0, column=1)

        ttk.Label(frame, text="Category").grid(row=0, column=2, padx=5)
        self.cat_var = tk.StringVar(value=CATEGORIES[0])
        ttk.Combobox(frame, textvariable=self.cat_var, values=CATEGORIES,
                     state="readonly", width=14).grid(row=0, column=3)

        ttk.Label(frame, text="Amount").grid(row=0, column=4, padx=5)
        self.amount_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.amount_var, width=10).grid(row=0, column=5)

        ttk.Label(frame, text="Note").grid(row=1, column=0, padx=5, pady=5)
        self.note_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.note_var, width=45).grid(
            row=1, column=1, columnspan=4, sticky="w")

        ttk.Button(frame, text="Add", command=self.add_expense).grid(row=1, column=5, padx=5)

    def _build_table(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10)
        ttk.Label(top, text="Filter month (YYYY-MM, blank = all):").pack(side="left")
        self.filter_var = tk.StringVar(value=date.today().strftime("%Y-%m"))
        ttk.Entry(top, textvariable=self.filter_var, width=10).pack(side="left", padx=5)
        ttk.Button(top, text="Apply", command=self.refresh).pack(side="left")
        ttk.Button(top, text="Export CSV", command=self.export_csv).pack(side="right")
        ttk.Button(top, text="Delete Selected", command=self.delete_selected).pack(side="right", padx=5)

        cols = ("date", "category", "amount", "note")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=10)
        for c, w in zip(cols, (110, 120, 90, 380)):
            self.tree.heading(c, text=c.title())
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)

        self.total_label = ttk.Label(self, text="Total: 0.00", font=("Arial", 12, "bold"))
        self.total_label.pack(anchor="e", padx=12)

    def _build_summary(self):
        frame = ttk.LabelFrame(self, text="Spending by Category")
        frame.pack(fill="both", padx=10, pady=8)
        self.canvas = tk.Canvas(frame, height=170, bg="white", highlightthickness=0)
        self.canvas.pack(fill="x", padx=5, pady=5)

    # ----- actions
    def add_expense(self):
        try:
            d, amount = validate(self.date_var.get(), self.amount_var.get())
        except ValueError as err:
            messagebox.showerror("Invalid input", str(err))
            return
        self.db.add(d, self.cat_var.get(), amount, self.note_var.get().strip())
        self.amount_var.set("")
        self.note_var.set("")
        self.refresh()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Delete", "Select a row first.")
            return
        if messagebox.askyesno("Confirm", "Delete the selected expense(s)?"):
            for item in selected:
                self.db.delete(int(item))  # row iid = database id
            self.refresh()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")])
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Category", "Amount", "Note"])
            for _, d, cat, amt, note in self.db.fetch(self._month()):
                writer.writerow([d, cat, amt, note])
        messagebox.showinfo("Export", "Expenses exported successfully.")

    def _month(self):
        return self.filter_var.get().strip() or None

    def refresh(self):
        month = self._month()
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = self.db.fetch(month)
        for exp_id, d, cat, amt, note in rows:
            self.tree.insert("", "end", iid=str(exp_id), values=(d, cat, f"{amt:.2f}", note))
        self.total_label.config(text=f"Total: {sum(r[3] for r in rows):.2f}")
        self.draw_chart(self.db.totals_by_category(month))

    def draw_chart(self, totals):
        """Simple bar chart drawn on a Canvas (no external libraries)."""
        self.canvas.delete("all")
        if not totals:
            self.canvas.create_text(200, 80, text="No data to show", fill="gray")
            return
        biggest = max(totals.values())
        x, bar_w, gap, base = 30, 60, 30, 135
        for cat, amt in sorted(totals.items(), key=lambda kv: -kv[1]):
            h = int((amt / biggest) * 100)
            self.canvas.create_rectangle(x, base - h, x + bar_w, base, fill="#4a90d9", outline="")
            self.canvas.create_text(x + bar_w / 2, base - h - 8, text=f"{amt:.0f}", font=("Arial", 9))
            self.canvas.create_text(x + bar_w / 2, base + 14, text=cat, font=("Arial", 9))
            x += bar_w + gap


if __name__ == "__main__":
    ExpenseApp().mainloop()
