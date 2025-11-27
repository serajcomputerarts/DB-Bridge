# 📦 DB-Bridge

**A Python-based tool to migrate MySQL databases to SQLite — created as part of a university database course project.**

---

## 📚 About the Project

**DB-Bridge** is a simple yet powerful Python script that automates the migration of a complete MySQL database into a SQLite database file.

This project was developed as part of a university **Database Systems** course to demonstrate practical knowledge of relational databases, data migration, and cross-platform compatibility between SQL engines.

---

## 🚀 Features

- ✅ Automatic detection of all tables in a MySQL database  
- ✅ Converts MySQL data types to SQLite-compatible types  
- ✅ Transfers all rows from each table (with batching for large datasets)  
- ✅ Preserves primary keys and auto-increment fields  
- ✅ Handles `Decimal`, `DateTime`, `BLOB`, and other complex types  
- ✅ Clean and readable code — easy to modify and extend  

---

## 🛠️ Requirements

Make sure you have Python 3.7+ installed.

Install required Python packages:

```bash
pip install mysql-connector-python
