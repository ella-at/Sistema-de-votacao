import sqlite3

DB_FILE = "database.db"

# Lista de produtos para inserir
produtos = [
("Swing Impact", "Keitech", "GRUPO WAKOKU / FLÓRIDA MARINE", "Isca Soft", 57.00, "Este não é um shad qualquer. Quando ele nada, o corpo inteiro se movimenta, tornando os movimentos mais naturais. Ele pode ser usado apenas com o anzol (lastreado ou não), no Texas Rig, Down Shot, jig head, como trailer de rubber jig, entre outras montagens. Já que possui diversos tamanhos. É uma ótima opção de isca para conseguir cobrir grandes áreas em menor tempo, além de ser muito produtivo durante todo o ano. O Swing Impact ainda é feito com material macio, impregnado com forte essência de lula. O corpo anelado que ainda serve para proteger a ponta do anzol.", "static/uploads/Swing.JPG")
]
# Conectar ao banco e inserir produtos
with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO produtos (nome, marca, expositor, categoria, valor, ficha_tecnica, foto)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        produtos
    )
    conn.commit()

print("Produtos inseridos com sucesso!")
