from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import csv
import os
import sqlite3
from werkzeug.utils import secure_filename
from flask_socketio import SocketIO, emit
from flask import Response


app = Flask(__name__)
app.secret_key = "chave_secreta"
socketio = SocketIO(app)  # Inicializa o WebSocket

app.secret_key = "chave_secreta"
DB_FILE = "database.db"
CPF_FILE = "cpfs_aprovados.csv"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Defina a pasta onde as imagens serão salvas
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Permitir apenas certas extensões de arquivo
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


###################
## novos intakes

# Conectar ao banco de dados
with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, marca, expositor, categoria, valor, ficha_tecnica, foto FROM produtos")
    produtos = cursor.fetchall()

# Criar arquivo CSV
with open("produtos_cadastrados.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["ID", "Nome", "Marca", "Expositor", "Categoria", "Valor", "Ficha Técnica", "Foto"])  # Cabeçalhos
    writer.writerows(produtos)

print("Arquivo 'produtos_cadastrados.csv' criado com sucesso!")

@app.route('/exportar_produtos_csv')
def exportar_produtos_csv():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, marca, expositor, categoria, valor, ficha_tecnica, foto FROM produtos")
        produtos = cursor.fetchall()

    # Criar o CSV em memória
    def gerar_csv():
        yield "ID,Nome,Marca,Expositor,Categoria,Valor,Ficha Técnica,Foto\n"
        for produto in produtos:
            linha = ','.join([str(campo) for campo in produto])
            yield linha + "\n"

    return Response(gerar_csv(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=produtos_cadastrados.csv"})

# nova tabela de votos
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
                cpf TEXT PRIMARY KEY,
                votou INTEGER DEFAULT 0
            )
        ''')

        # Tabela para armazenar os votos por categoria
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT NOT NULL,
                categoria TEXT NOT NULL,
                produto_id INTEGER NOT NULL,
                data_voto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(cpf) REFERENCES votantes(cpf),
                FOREIGN KEY(produto_id) REFERENCES produtos(id),
                UNIQUE(cpf, categoria)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_votos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT NOT NULL,
                categoria TEXT NOT NULL,
                produto_id INTEGER NOT NULL,
                data_voto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(cpf) REFERENCES votantes(cpf),
                FOREIGN KEY(produto_id) REFERENCES produtos(id)
            )
        ''')

        
        
        
        conn.commit()

init_db()

# RESETAR VOTAÇÃO
@app.route('/resetar_votacao', methods=['POST'])
def resetar_votacao():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Zerar os votos dos votantes
        cursor.execute("UPDATE votantes SET votou = 0, voto_produto = NULL")

        # Apagar todos os votos registrados na tabela de votos
        cursor.execute("DELETE FROM votos")

        conn.commit()

    # Enviar evento WebSocket para atualizar as telas em tempo real
    socketio.emit("atualizar_votacao")

    return jsonify({"message": "Votação resetada com sucesso!"})



# novo intake
@app.route('/exportar_votos_csv')
def exportar_votos_csv():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.cpf, p.nome 
            FROM votantes v
            JOIN produtos p ON v.voto_produto = p.id
            WHERE v.votou = 1
        """)
        votos = cursor.fetchall()

    # Criar o CSV em memória
    def gerar_csv():
        yield "CPF,Produto Votado\n"
        for voto in votos:
            linha = ','.join([str(campo) for campo in voto])
            yield linha + "\n"

    return Response(gerar_csv(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=votos_realizados.csv"})

# Conectar ao banco de dados
with sqlite3.connect(DB_FILE) as conn:
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.cpf, p.categoria, p.nome
        FROM votantes v
        JOIN produtos p ON v.voto_produto = p.id
        WHERE v.votou = 1
        ORDER BY v.cpf, p.categoria
    """)
    votos = cursor.fetchall()

# Criar arquivo CSV
with open("votos_por_categoria.csv", "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["CPF", "Categoria", "Produto Votado"])  # Cabeçalhos
    writer.writerows(votos)

print("Arquivo 'votos_por_categoria.csv' criado com sucesso!")


@app.route('/exportar_votos_categoria_csv')
def exportar_votos_categoria_csv():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT v.cpf, p.categoria, p.nome
            FROM votos v
            JOIN produtos p ON v.produto_id = p.id
            ORDER BY v.cpf, p.categoria
        """)
        votos = cursor.fetchall()

    # Salva no disco
    with open("votos_por_categoria.csv", "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["CPF", "Categoria", "Produto Votado"])
        writer.writerows(votos)

    print("Arquivo 'votos_por_categoria.csv' criado com sucesso!")

    # Permite download direto
    def gerar_csv():
        yield "CPF,Categoria,Produto Votado\n"
        for voto in votos:
            yield ','.join([str(campo) for campo in voto]) + "\n"

    return Response(
        gerar_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=votos_por_categoria.csv"}
    )

#############################

# Página de upload cpf
@app.route("/arquivo_cpf")
def arquivo_cpf():
    return render_template("arquivo_cpf.html")


# Função para validar CPF
def validar_cpf(cpf):
    cpf = "".join(filter(str.isdigit, cpf))  # Remove caracteres não numéricos
    return len(cpf) == 11 and not cpf.count(cpf[0]) == 11  # Evita CPFs inválidos


# Rota para processar o upload
@app.route("/upload_cpfs", methods=["POST"])
def upload_cpfs():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado!"}), 400

    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado!"}), 400

    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Apenas arquivos .csv são permitidos!"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
    file.save(file_path)

    inserted = 0
    duplicates = 0
    invalids = 0

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votantes (
                cpf TEXT PRIMARY KEY,
                votou INTEGER DEFAULT 0,
                voto_produto INTEGER,
                FOREIGN KEY(voto_produto) REFERENCES produtos(id)
            )
        ''')

        with open(file_path, newline='', encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                cpf = row[0].strip()

                if not validar_cpf(cpf):
                    invalids += 1
                    continue  # Pula CPFs inválidos

                cursor.execute("SELECT cpf FROM votantes WHERE cpf = ?", (cpf,))
                if cursor.fetchone():
                    duplicates += 1  # CPF já cadastrado
                else:
                    cursor.execute("INSERT INTO votantes (cpf, votou) VALUES (?, 0)", (cpf,))
                    inserted += 1  # CPF novo cadastrado

        conn.commit()

    return jsonify({"inserted": inserted, "duplicates": duplicates, "invalids": invalids})

# Página de upload de produtos
@app.route("/arquivo_produto")
def arquivo_produto():
    return render_template("arquivo_produto.html")

# Rota para processar o upload
@app.route("/upload_produtos", methods=["POST"])
def upload_produtos():
    if "file" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado!"}), 400

    file = request.files["file"]
    
    if file.filename == "":
        return jsonify({"error": "Nenhum arquivo selecionado!"}), 400

    if not file.filename.endswith(".csv"):
        return jsonify({"error": "Apenas arquivos .csv são permitidos!"}), 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(file.filename))
    file.save(file_path)

    inserted = 0
    duplicates = 0
    invalids = 0

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
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

        with open(file_path, newline='', encoding="ISO-8859-1", errors='replace') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) < 7:  # Verifica se há colunas suficientes
                    invalids += 1
                    continue

                nome, marca, expositor, categoria, valor, ficha_tecnica, foto = map(str.strip, row)

                if not nome or not marca or not categoria or not valor:  # Evita produtos inválidos
                    invalids += 1
                    continue

                cursor.execute("SELECT id FROM produtos WHERE nome = ? AND marca = ?", (nome, marca))
                if cursor.fetchone():
                    duplicates += 1  # Produto já cadastrado
                else:
                    cursor.execute('''INSERT INTO produtos 
                        (nome, marca, expositor, categoria, valor, ficha_tecnica, foto) 
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                        (nome, marca, expositor, categoria, float(valor), ficha_tecnica, foto))
                    inserted += 1  # Produto novo cadastrado

        conn.commit()

    return jsonify({"inserted": inserted, "duplicates": duplicates, "invalids": invalids})


# Criando banco de dados SQLite
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votantes (
                cpf TEXT PRIMARY KEY,
                votou INTEGER DEFAULT 0,
                voto_produto INTEGER,
                FOREIGN KEY(voto_produto) REFERENCES produtos(id)
            )
        ''')
        conn.commit()

init_db()

# Carregar CPFs aprovados
def carregar_cpfs():
    cpfs = set()
    if os.path.exists(CPF_FILE):
        with open(CPF_FILE, "r") as file:
            reader = csv.reader(file)
            for row in reader:
                cpfs.add(row[0])
    return cpfs

CPFs_APROVADOS = carregar_cpfs()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/cadastro_produto', methods=['GET', 'POST'])
def cadastro_produto():
    if request.method == 'POST':
        nome = request.form['nome']
        marca = request.form['marca']
        expositor = request.form['expositor']
        categoria = request.form['categoria']
        valor = float(request.form['valor'])
        ficha_tecnica = request.form['ficha_tecnica']
        foto = request.files['foto']
        
        if foto:
            foto_path = os.path.join(UPLOAD_FOLDER, foto.filename)
            foto.save(foto_path)
        else:
            foto_path = ""
        
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO produtos (nome, marca, expositor, categoria, valor, ficha_tecnica, foto) VALUES (?, ?, ?, ?, ?, ?, ?)''',
                           (nome, marca, expositor, categoria, valor, ficha_tecnica, foto_path))
            conn.commit()
        flash("Produto cadastrado com sucesso!")
        return redirect(url_for('index'))
    return render_template("cadastro_produto.html")



@app.route('/cadastro_cpf', methods=['GET', 'POST'])
def cadastro_cpf():
    if request.method == 'POST':
        cpf = request.form['cpf'].strip()  # Remover espaços extras

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

            # Verificar se o CPF já está cadastrado
            cursor.execute("SELECT cpf FROM votantes WHERE cpf = ?", (cpf,))
            existente = cursor.fetchone()

            if existente:
                flash("CPF já cadastrado!", "warning")
            else:
                # Adicionar CPF ao banco de dados
                cursor.execute("INSERT INTO votantes (cpf, votou) VALUES (?, 0)", (cpf,))
                conn.commit()
                flash("CPF cadastrado com sucesso!", "success")

        return redirect(url_for('cadastro_cpf'))

    return render_template("cadastro_cpf.html")

@app.route('/cadastrar_cpf', methods=['POST'])
def cadastrar_cpf():
    data = request.get_json()
    cpf = data.get('cpf')

    if not cpf:
        return jsonify({"error": "CPF não informado!"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Criar a tabela caso não exista
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votantes (
                cpf TEXT PRIMARY KEY,
                votou INTEGER DEFAULT 0,
                voto_produto INTEGER,
                FOREIGN KEY(voto_produto) REFERENCES produtos(id)
            )
        ''')

        # Verificar se o CPF já existe no banco
        cursor.execute("SELECT cpf FROM votantes WHERE cpf = ?", (cpf,))
        if cursor.fetchone():
            return jsonify({"error": "Este CPF já está cadastrado!"}), 409

        # Inserir CPF no banco
        cursor.execute("INSERT INTO votantes (cpf, votou) VALUES (?, 0)", (cpf,))
        conn.commit()

    return jsonify({"message": "CPF cadastrado com sucesso!"}), 200


@app.route('/lista_produtos')
def lista_produtos():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, categoria, foto FROM produtos ORDER BY categoria, nome")
        produtos = cursor.fetchall()
    return render_template("lista_produtos.html", produtos=produtos)



@app.route('/lista_produtos_json')
def lista_produtos_json():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, marca, expositor, categoria, valor, ficha_tecnica, foto FROM produtos ORDER BY categoria, nome")
        produtos = [
            {
                "id": row[0],
                "nome": row[1],
                "marca": row[2],
                "expositor": row[3],
                "categoria": row[4],
                "valor": row[5],
                "ficha_tecnica": row[6],
                "imagem": row[7]  # O caminho da imagem salva no banco
            }
            for row in cursor.fetchall()
        ]
    return jsonify(produtos)


@app.route('/excluir_produto/<int:produto_id>', methods=['POST'])
def excluir_produto(produto_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))
        conn.commit()
    flash("Produto excluído com sucesso!", "success")
    return '', 204  # Responde sem conteúdo para a requisição AJAX



@app.route("/lista_votantes")
def lista_votantes():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT cpf, votou, voto_produto FROM votantes")
    votantes = cursor.fetchall()  
    conn.close()
    
    total_votaram = sum(1 for _, votou, _ in votantes if votou == 1)
    total_nao_votaram = len(votantes) - total_votaram
    
    return render_template("lista_votantes.html", 
                           votantes=votantes,
                            total_votaram=total_votaram,
                            total_nao_votaram=total_nao_votaram)


@app.route('/resultados_premio')
def resultados_premio():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.categoria, p.nome, p.marca, p.foto, COUNT(v.produto_id) AS votos
            FROM votos v
            JOIN produtos p ON v.produto_id = p.id
            GROUP BY p.id
            ORDER BY p.categoria, votos DESC
        """)
        resultados = cursor.fetchall()

    # Organizar o mais votado por categoria
    categorias = {}
    for categoria, nome, marca, foto, votos in resultados:
        if categoria not in categorias:
            categorias[categoria] = [{
                "nome": nome,
                "marca": marca,
                "foto": foto,
                "votos": votos
            }]

    return render_template("resultados_premio.html", resultados=categorias)






#@app.route('/votacao', methods=['GET', 'POST'])
#def votacao():
   # if request.method == 'POST':
       # cpf = request.form['cpf'].strip()
       # with sqlite3.connect(DB_FILE) as conn:
           # cursor = conn.cursor()
            # Verificar se o CPF está cadastrado e se já votou
           # cursor.execute("SELECT votou FROM votantes WHERE cpf = ?", (cpf,))
           # votante = cursor.fetchone()
          #  if not votante:
         #       return jsonify({"error": "CPF não cadastrado!"}), 400
        #    if votante[0] == 1:
       #         return jsonify({"error": "Este CPF já votou!"}), 403
            # Buscar produtos para exibição na votação
      #      cursor.execute("SELECT id, nome, categoria, foto FROM produtos ORDER BY categoria, nome")
     #       produtos = [{"id": row[0], "nome": row[1], "categoria": row[2], "foto": row[3]} for row in cursor.fetchall()]
    #    return jsonify({"cpf_valido": True, "produtos": produtos})
   # return render_template("votacao.html")
   

# Rota para carregar os produtos
@app.route("/votacao", methods=["GET", "POST"])
def votacao():
    if request.method == "GET":
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, nome, categoria, foto FROM produtos ORDER BY categoria, nome")
            produtos = cursor.fetchall()

        # Organizar produtos por categoria
        categorias = {}
        for produto in produtos:
            categoria = produto[2]
            if categoria not in categorias:
                categorias[categoria] = []
            categorias[categoria].append({"id": produto[0], "nome": produto[1], "foto": produto[3]})

        return render_template("votacao.html", categorias=categorias)

    # Se for POST, valida CPF e retorna os produtos via JSON (caso necessário)
    cpf = request.form.get("cpf")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT votou FROM votantes WHERE cpf = ?", (cpf,))
        votante = cursor.fetchone()

        if not votante:
            return jsonify({"cpf_valido": False, "error": "CPF não autorizado para votar!"})

        if votante[0] == 1:
            return jsonify({"cpf_valido": False, "error": "Este CPF já votou!"})

        cursor.execute("SELECT id, nome, categoria, foto FROM produtos ORDER BY categoria, nome")
        produtos = [{"id": row[0], "nome": row[1], "categoria": row[2], "foto": row[3]} for row in cursor.fetchall()]

    return jsonify({"cpf_valido": True, "produtos": produtos})




# Rota para confirmar o voto
@app.route("/confirmar_voto", methods=["POST"])
def confirmar_voto():
    cpf = request.form["cpf"]
    produto_id = request.form["produto_id"]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Atualiza a votação
        cursor.execute("UPDATE votantes SET votou = 1, voto_produto = ? WHERE cpf = ?", (produto_id, cpf))
        conn.commit()

        # **Envia atualização para todos os dispositivos**
        socketio.emit("atualizar_votacao", {"cpf": cpf, "produto_id": produto_id})

    return jsonify({"message": "Voto registrado com sucesso!"})


@app.route("/apagar_cpf", methods=["POST"])
def apagar_cpf():
    data = request.get_json()
    cpf = data.get("cpf")

    if not cpf:
        return jsonify({"error": "CPF não informado!"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Verificar se o CPF existe no banco
        cursor.execute("SELECT cpf FROM votantes WHERE cpf = ?", (cpf,))
        votante = cursor.fetchone()
        if not votante:
            return jsonify({"error": "CPF não encontrado!"}), 404

        # Deletar votos do CPF antes de removê-lo do banco de dados
        cursor.execute("DELETE FROM votos WHERE cpf = ?", (cpf,))
        cursor.execute("DELETE FROM votantes WHERE cpf = ?", (cpf,))
        conn.commit()

    return jsonify({"message": f"CPF {cpf} e seus votos foram removidos com sucesso!"}), 200


@app.route('/voto_categoria')
def voto_categoria():
    return render_template("voto_categoria.html")


# Atualiza todos os dispositivos quando um voto é confirmado
@app.route("/confirmar_voto_categoria", methods=["POST"])
def confirmar_voto_categoria():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Nenhum dado recebido"}), 400

    cpf = data.get("cpf")
    votos = data.get("votos", {})

    if not cpf or not votos:
        return jsonify({"error": "CPF ou votos ausentes!"}), 400

    print(f"Recebido CPF: {cpf}, Votos: {votos}")  # Log para depuração

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Verificar se o CPF existe
        cursor.execute("SELECT cpf FROM votantes WHERE cpf = ?", (cpf,))
        if not cursor.fetchone():
            return jsonify({"error": "CPF não autorizado para votar!"}), 403

        # Inserir ou substituir os votos na tabela
        for categoria, produto_id in votos.items():
            cursor.execute("""
                INSERT INTO votos (cpf, categoria, produto_id)
                VALUES (?, ?, ?)
                ON CONFLICT(cpf, categoria) DO UPDATE SET produto_id = excluded.produto_id
            """, (cpf, categoria, produto_id))

        # Atualizar que o usuário votou
        cursor.execute("UPDATE votantes SET votou = 1 WHERE cpf = ?", (cpf,))

        conn.commit()

    # Atualizar página em tempo real via WebSocket
    socketio.emit("atualizar_votacao")

    return jsonify({"message": "Votos confirmados com sucesso!"})

# rota para mostrar quantos já votaram e quantos não votaram
@app.route('/contagem_votantes')
def contagem_votantes():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM votantes")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM votantes WHERE votou = 1")
        votaram = cursor.fetchone()[0]
        nao_votaram = total - votaram

    return jsonify({
        "total_cadastrados": total,
        "total_votaram": votaram,
        "total_nao_votaram": nao_votaram
    })




@app.route('/api/votacao_resultado')
def api_resultado_votacao():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Consulta para contar os votos por categoria e ordenar os mais votados primeiro
        cursor.execute('''
            SELECT p.categoria, p.nome, p.foto, COUNT(v.produto_id) as votos
            FROM votos v
            JOIN produtos p ON v.produto_id = p.id
            GROUP BY p.id, p.categoria
            ORDER BY p.categoria, votos DESC
        ''')

        resultados = cursor.fetchall()

    # Organizar os resultados por categoria
    categorias = {}
    total_votos = sum(votos for _, _, _, votos in resultados)  # Total geral

    for categoria, nome, foto, votos in resultados:
        if categoria not in categorias:
            categorias[categoria] = []
        porcentagem = (votos / total_votos * 100) if total_votos > 0 else 0
        categorias[categoria].append({
            "nome": nome,
            "foto": foto,
            "votos": votos,
            "porcentagem": round(porcentagem, 2)
        })

    return jsonify(categorias)






@app.route('/produtos_por_categoria')
def produtos_por_categoria():
    categoria = request.args.get("categoria")
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, foto FROM produtos WHERE categoria = ?", (categoria,))
        produtos = [{"id": row[0], "nome": row[1], "foto": row[2]} for row in cursor.fetchall()]
    return jsonify(produtos)



@app.route('/votacao_resultado')
def resultado_votacao():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Consulta para contar os votos por categoria e ordenar os mais votados primeiro
        cursor.execute('''
            SELECT p.categoria, p.nome, p.foto, COUNT(v.voto_produto) as votos
            FROM produtos p
            LEFT JOIN votantes v ON p.id = v.voto_produto
            GROUP BY p.id
            ORDER BY p.categoria, votos DESC
        ''')

        resultados = cursor.fetchall()

    # Organizar os resultados por categoria
    categorias = {}
    for categoria, nome, foto, votos in resultados:
        if categoria not in categorias:
            categorias[categoria] = []
        categorias[categoria].append((nome, foto, votos))

    return render_template("votacao_resultado.html", resultados=categorias)





@app.route("/salvar_produto", methods=["POST"])
def salvar_produto():
    nome = request.form["nome"]
    marca = request.form["marca"]
    expositor = request.form["expositor"]
    categoria = request.form["categoria"]
    valor = request.form["valor"]
    ficha_tecnica = request.form["ficha_tecnica"]

    # Verificar se um arquivo foi enviado
    if "foto" not in request.files:
        return "Erro: Nenhum arquivo enviado!"

    file = request.files["foto"]

    if file.filename == "":
        return "Erro: Nenhum arquivo selecionado!"

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
        foto = f"static/uploads/{filename}"
    else:
        return "Erro: Formato de arquivo não permitido!"

    # Salvar no banco de dados
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO produtos (nome, marca, expositor, categoria, valor, ficha_tecnica, foto) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (nome, marca, expositor, categoria, valor, ficha_tecnica, foto),
    )
    conn.commit()
    conn.close()

    return render_template("salvar_produto.html")


@app.route('/informacoes')
def informacoes():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nome, marca, expositor, categoria, valor, ficha_tecnica, foto FROM produtos ORDER BY categoria, nome")
        produtos = cursor.fetchall()

    produtos_formatados = [
        {
            "id": row[0],
            "nome": row[1],
            "marca": row[2],
            "expositor": row[3],
            "categoria": row[4],
            "valor": row[5],
            "ficha_tecnica": row[6],
            "imagem": row[7]  # Caminho da imagem do produto
        }
        for row in produtos
    ]
    
    return render_template("informacoes.html", produtos=produtos_formatados)

########### historico de votos
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()

        # Criar tabela de produtos
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

        # Criar tabela de votantes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votantes (
                cpf TEXT PRIMARY KEY,
                votou INTEGER DEFAULT 0
            )
        ''')

        # Criar tabela de votos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT NOT NULL,
                categoria TEXT NOT NULL,
                produto_id INTEGER NOT NULL,
                FOREIGN KEY(cpf) REFERENCES votantes(cpf),
                FOREIGN KEY(produto_id) REFERENCES produtos(id),
                UNIQUE(cpf, categoria)
            )
        ''')

        # Criar tabela de histórico de votos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_votos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT NOT NULL,
                categoria TEXT NOT NULL,
                produto_id INTEGER NOT NULL,
                data_voto TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(cpf) REFERENCES votantes(cpf),
                FOREIGN KEY(produto_id) REFERENCES produtos(id)
            )
        ''')

        conn.commit()


@app.route('/exportar_historico_votos_csv')
def exportar_historico_votos_csv():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT h.cpf, h.categoria, p.nome, h.data_voto
            FROM historico_votos h
            JOIN produtos p ON h.produto_id = p.id
            ORDER BY h.data_voto DESC
        """)
        historico_votos = cursor.fetchall()

    # Criar o CSV em memória
    def gerar_csv():
        yield "CPF,Categoria,Produto,Votado Em\n"
        for voto in historico_votos:
            linha = ','.join([str(campo) for campo in voto])
            yield linha + "\n"

    return Response(gerar_csv(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=historico_votos.csv"})

######
# Rota para apresentar o produto mais votado por categoria
@app.route('/apresentacao')
def apresentacao():
    categoria = request.args.get('categoria')
    if not categoria:
        return "Categoria não especificada", 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.nome, p.foto, COUNT(v.produto_id) as votos
            FROM votos v
            JOIN produtos p ON v.produto_id = p.id
            WHERE p.categoria = ?
            GROUP BY p.id
            ORDER BY votos DESC
            LIMIT 1
        """, (categoria,))
        resultado = cursor.fetchone()

    if not resultado:
        return f"Nenhum voto encontrado para a categoria '{categoria}'", 404

    produto = {
        "nome": resultado[0],
        "foto": resultado[1],
        "votos": resultado[2]
    }

    return render_template("apresentacao.html", categoria=categoria, produto=produto)


@app.route('/api/vencedor_categoria')
def api_vencedor_categoria():
    categoria = request.args.get('categoria')
    if not categoria:
        return jsonify({"error": "Categoria não especificada"}), 400

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.nome, p.marca, p.foto, COUNT(v.produto_id) as votos
            FROM votos v
            JOIN produtos p ON v.produto_id = p.id
            WHERE p.categoria = ?
            GROUP BY p.id
            ORDER BY votos DESC
            LIMIT 1
        """, (categoria,))
        resultado = cursor.fetchone()

    if not resultado:
        return jsonify({"error": "Nenhum vencedor encontrado para esta categoria."}), 404

    return jsonify({
        "categoria": categoria,
        "nome": resultado[0],
        "marca": resultado[1],
        "foto": resultado[2],
        "votos": resultado[3]
    })




# WebSocket: Atualizar todos os iPads em tempo real
@socketio.on("atualizar_votacao")
def atualizar_votacao(data):
    emit("atualizar_votacao", data, broadcast=True)
    
    


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=5000, allow_unsafe_werkzeug=True)
    
