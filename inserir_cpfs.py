import sqlite3

DB_FILE = "database.db"

# Lista de CPFs para inserir
cpfs = [
"000.000.000-00",
"000.000.000-00",
]

# Conectar ao banco e inserir CPFs
with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.cursor()

    # Criar a tabela de votantes, caso não exista
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votantes (
            cpf TEXT PRIMARY KEY,
            votou INTEGER DEFAULT 0,
            voto_produto INTEGER,
            FOREIGN KEY(voto_produto) REFERENCES produtos(id)
        )
    ''')

    # Inserir os CPFs no banco de dados
    for cpf in cpfs:
        try:
            cursor.execute("INSERT INTO votantes (cpf, votou) VALUES (?, 0)", (cpf,))
        except sqlite3.IntegrityError:
            print(f"CPF {cpf} já está cadastrado.")

    conn.commit()

print("CPFs cadastrados com sucesso no banco de dados!")
