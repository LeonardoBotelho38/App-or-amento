from flask import Flask, render_template, request, redirect
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

# Banco de dados dos pontos (agora o correto)
DB_PONTOS = 'database.db'
# Banco de dados dos orçamentos
DB_ORCAMENTOS = 'orcamentos.db'

def init_db():
    with sqlite3.connect(DB_PONTOS) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contratos (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                cidade TEXT,
                tipo_midia TEXT,
                periodo TEXT,
                valor_fornecedor REAL,
                fornecedor TEXT
            )
        ''')
    with sqlite3.connect(DB_ORCAMENTOS) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orcamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cidade TEXT,
                tipo_midia TEXT,
                quantidade_pontos INTEGER,
                quantidade_bissemana INTEGER,
                material TEXT,
                valor_total_cliente REAL,
                valor_total_fornecedor REAL,
                lucro REAL,
                data_criacao TEXT,
                dados TEXT
            )
        ''')

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        cidade = request.form['cidade']
        tipo_midia = request.form['tipo']
        periodo = request.form['periodo']
        valor_fornecedor = float(request.form['valor'])
        fornecedor = request.form['fornecedor']

        with sqlite3.connect(DB_PONTOS) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO contratos (cidade, tipo_midia, periodo, valor_fornecedor, fornecedor)
                VALUES (?, ?, ?, ?, ?)
            ''', (cidade, tipo_midia, periodo, valor_fornecedor, fornecedor))
            conn.commit()
        return redirect('/')
    return render_template('cadastro.html')

@app.route('/orcamento', methods=['GET', 'POST'])
def orcamento():
    if request.method == 'POST':
        pontos = request.form.getlist('ponto')
        imposto = float(request.form['imposto']) / 100
        custo_papel = float(request.form['custo_papel'])
        custo_lona = float(request.form['custo_lona'])
        margem_lucro = float(request.form['margem_lucro']) / 100

        total_cliente = 0
        total_fornecedor = 0
        dados_detalhados = []

        with sqlite3.connect(DB_PONTOS) as conn:
            cursor_contratos = conn.cursor()
            for ponto_str in pontos:
                cidade, tipo, qtd_str, bisemanas_str, material = ponto_str.split('|')
                qtd = int(qtd_str)
                bisemanas = int(bisemanas_str)
                cursor_contratos.execute('SELECT valor_fornecedor FROM contratos WHERE cidade=? AND tipo_midia=? LIMIT 1', (cidade, tipo))
                row = cursor_contratos.fetchone()
                if row:
                    valor_fornecedor_unitario = row[0]
                    custo_material = custo_papel if material == 'papel' else custo_lona
                    subtotal_fornecedor = (valor_fornecedor_unitario + custo_material) * qtd * bisemanas
                    subtotal_cliente_liquido = subtotal_fornecedor * (1 + margem_lucro)
                    subtotal_cliente = subtotal_cliente_liquido * (1 + imposto)
                    total_fornecedor += subtotal_fornecedor
                    total_cliente += subtotal_cliente
                    dados_detalhados.append(f"{qtd}x {tipo} em {cidade} por {bisemanas} bi-semanas usando {material}: R${subtotal_cliente:.2f}")

        lucro = total_cliente - total_fornecedor
        dados_string = '; '.join(dados_detalhados)
        data_criacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Salvar no banco de orçamentos
        with sqlite3.connect(DB_ORCAMENTOS) as conn:
            cursor_orcamentos = conn.cursor()
            if pontos:
                cidade_exemplo, tipo_exemplo, _, bisemanas_exemplo, material_exemplo = pontos[0].split('|')
                cursor_orcamentos.execute('''
                    INSERT INTO orcamentos (cidade, tipo_midia, quantidade_pontos, quantidade_bissemana, material, valor_total_cliente, valor_total_fornecedor, lucro, data_criacao, dados)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (cidade_exemplo, tipo_exemplo, len(pontos), sum(int(p.split('|')[3]) for p in pontos), material_exemplo, total_cliente, total_fornecedor, lucro, data_criacao, dados_string))
                conn.commit()

        return render_template('orcamento_resultado.html', dados=dados_detalhados, total=total_cliente)

    else:
        # Coleta cidades e tipos disponíveis DA TABELA CORRETA 'contratos'
        with sqlite3.connect(DB_PONTOS) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT cidade FROM contratos')
            cidades = [row[0] for row in cursor.fetchall()]
            cursor.execute('SELECT DISTINCT tipo_midia FROM contratos')
            tipos = [row[0] for row in cursor.fetchall()]

        return render_template('orcamento.html', cidades=cidades, tipos=tipos)

if __name__ == '__main__':
    app.run(debug=True)