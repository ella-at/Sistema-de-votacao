import sqlite3
import pandas as pd

# Nome do banco de dados SQLite
DB_FILE = "database.db"

# Nome do arquivo CSV
CSV_FILE = "produtos_corrigidos_final.csv"

# Conectar ao banco de dados SQLite
conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Tabela de Produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                marca TEXT NOT NULL,
                expositor TEXT NOT NULL,
                categoria TEXT NOT NULL,
                valor REAL NOT NULL,
                ficha_tecnica TEXT NOT NULL,
                foto TEXT NOT NULL
            )
        ''')

        # Tabela de Votantes (apenas o CPF)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votantes (
                cpf TEXT PRIMARY KEY
            )
        ''')

        # Tabela para armazenar os votos por categoria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT NOT NULL,
                categoria TEXT NOT NULL,
                produto_id INTEGER NOT NULL,
                FOREIGN KEY(cpf) REFERENCES votantes(cpf),
                FOREIGN KEY(produto_id) REFERENCES produtos(id),
                UNIQUE(cpf, categoria) -- Garante um voto por categoria por CPF
            )
        ''')

        conn.commit()

init_db()


# Criar a tabela caso não exista
cursor.execute('''
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        marca TEXT NOT NULL,
        expositor TEXT NOT NULL,
        categoria TEXT NOT NULL,
        valor REAL NOT NULL,
        ficha_tecnica TEXT NOT NULL,
        foto TEXT NOT NULL
    )
''')

# Ler o CSV
df = pd.read_csv(CSV_FILE, delimiter=",", encoding="utf-8")

# Verificar se a coluna "Valor" está correta
df["Valor"] = df["Valor"].astype(str).str.replace(",", ".")  # Ajustar separadores decimais
df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")  # Converter para float

# Remover linhas com valores inválidos
df = df.dropna(subset=["Nome", "Marca", "Expositor", "Categoria", "Valor", "Ficha Técnica", "Foto"])

# Contadores para verificar quantos registros são inseridos
total_linhas = len(df)
linhas_inseridas = 0

# Inserir os dados no banco de dados
for _, row in df.iterrows():
    try:
        cursor.execute('''
            INSERT INTO produtos (nome, marca, expositor, categoria, valor, ficha_tecnica, foto)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (row["Nome"], row["Marca"], row["Expositor"], row["Categoria"], row["Valor"], row["Ficha Técnica"], row["Foto"]))
        linhas_inseridas += 1
    except Exception as e:
        print(f"Erro ao inserir linha: {row.to_dict()} - Erro: {e}")

# Salvar as mudanças no banco de dados
conn.commit()

# Fechar conexão
conn.close()

# Mensagem final
print(f"✅ Importação concluída! {linhas_inseridas} de {total_linhas} produtos adicionados ao banco de dados.")
