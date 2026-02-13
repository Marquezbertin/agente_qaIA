"""
Script para criar banco de dados de demonstracao
==================================================

Cria um banco SQLite com dados FICTICIOS para demonstrar
as funcionalidades do QA Agent sem precisar de dados reais.

Uso:
    python scripts/create_sample_db.py

O banco sera criado em: data/sample_test_data.db
"""

import sqlite3
import os
from pathlib import Path


def generate_valid_cpf(base_digits: list) -> str:
    """
    Gera um CPF valido a partir de 9 digitos base.
    Calcula os 2 digitos verificadores usando o algoritmo oficial.
    """
    # Primeiro digito verificador
    weights1 = [10, 9, 8, 7, 6, 5, 4, 3, 2]
    sum1 = sum(d * w for d, w in zip(base_digits, weights1))
    d1 = 11 - (sum1 % 11)
    d1 = 0 if d1 >= 10 else d1

    # Segundo digito verificador
    digits_with_d1 = base_digits + [d1]
    weights2 = [11, 10, 9, 8, 7, 6, 5, 4, 3, 2]
    sum2 = sum(d * w for d, w in zip(digits_with_d1, weights2))
    d2 = 11 - (sum2 % 11)
    d2 = 0 if d2 >= 10 else d2

    cpf = ''.join(str(d) for d in base_digits) + str(d1) + str(d2)
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"


def generate_valid_cnpj(base_digits: list) -> str:
    """
    Gera um CNPJ valido a partir de 12 digitos base.
    Calcula os 2 digitos verificadores usando o algoritmo oficial.
    """
    # Primeiro digito verificador
    weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum1 = sum(d * w for d, w in zip(base_digits, weights1))
    d1 = 11 - (sum1 % 11)
    d1 = 0 if d1 >= 10 else d1

    # Segundo digito verificador
    digits_with_d1 = base_digits + [d1]
    weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    sum2 = sum(d * w for d, w in zip(digits_with_d1, weights2))
    d2 = 11 - (sum2 % 11)
    d2 = 0 if d2 >= 10 else d2

    cnpj = ''.join(str(d) for d in base_digits) + str(d1) + str(d2)
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def create_database():
    """Cria o banco de dados de demonstracao com dados ficticios."""

    db_dir = Path(__file__).parent.parent / "data"
    db_dir.mkdir(exist_ok=True)
    db_path = db_dir / "sample_test_data.db"

    # Remover banco existente se houver
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # =============================================
    # Tabela: individuos (CPFs ficticios)
    # =============================================
    cursor.execute("""
        CREATE TABLE individuos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT,
            nome_original TEXT,
            nome_validado TEXT,
            restricao TEXT,
            status_validacao TEXT
        )
    """)

    # 10 CPFs ficticios com nomes inventados
    individuos = [
        ([1, 2, 3, 4, 5, 6, 7, 8, 9], "Joao da Silva Teste", "JOAO DA SILVA TESTE", None, "VALIDADO"),
        ([9, 8, 7, 6, 5, 4, 3, 2, 1], "Maria Oliveira Demo", "MARIA OLIVEIRA DEMO", None, "VALIDADO"),
        ([1, 1, 1, 4, 4, 4, 7, 7, 7], "Carlos Santos Exemplo", "CARLOS SANTOS EXEMPLO", None, "VALIDADO"),
        ([2, 2, 2, 5, 5, 5, 8, 8, 8], "Ana Pereira Sample", "ANA PEREIRA SAMPLE", None, "VALIDADO"),
        ([3, 3, 3, 6, 6, 6, 9, 9, 9], "Pedro Costa Ficticio", "PEDRO COSTA FICTICIO", "SPC", "VALIDADO"),
        ([4, 5, 6, 7, 8, 9, 0, 1, 2], "Lucia Ferreira Test", "LUCIA FERREIRA TEST", None, "VALIDADO"),
        ([5, 6, 7, 8, 9, 0, 1, 2, 3], "Roberto Almeida QA", "ROBERTO ALMEIDA QA", "SERASA", "VALIDADO"),
        ([6, 7, 8, 9, 0, 1, 2, 3, 4], "Fernanda Lima Demo", "FERNANDA SOUZA DEMO", None, "NOME DIVERGENTE"),
        ([7, 8, 9, 0, 1, 2, 3, 4, 5], "Ricardo Souza Teste", "RICARDO SOUZA TESTE", None, "VALIDADO"),
        ([8, 9, 0, 1, 2, 3, 4, 5, 6], "Patricia Rocha Sample", "PATRICIA ROCHA SAMPLE", None, "VALIDADO"),
    ]

    for base_digits, nome_orig, nome_valid, restricao, status in individuos:
        cpf = generate_valid_cpf(base_digits)
        cursor.execute(
            "INSERT INTO individuos (cpf, nome_original, nome_validado, restricao, status_validacao) VALUES (?, ?, ?, ?, ?)",
            (cpf, nome_orig, nome_valid, restricao, status)
        )

    # =============================================
    # Tabela: empresas (CNPJs ficticios)
    # =============================================
    cursor.execute("""
        CREATE TABLE empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cnpj TEXT,
            nome_original TEXT,
            nome_validado TEXT,
            endereco TEXT,
            cidade TEXT,
            estado TEXT,
            cep TEXT,
            situacao_cadastral TEXT,
            status_validacao TEXT
        )
    """)

    empresas = [
        ([1, 1, 2, 2, 2, 0, 0, 0, 0, 1, 0, 1], "Empresa Teste LTDA", "EMPRESA TESTE LTDA",
         "Rua Exemplo 123", "Sao Paulo", "SP", "01001-000", "ATIVA", "VALIDADO"),
        ([2, 2, 3, 3, 3, 0, 0, 0, 0, 1, 0, 1], "Demo Tecnologia SA", "DEMO TECNOLOGIA SA",
         "Av Demo 456", "Rio de Janeiro", "RJ", "20040-020", "ATIVA", "VALIDADO"),
        ([3, 3, 4, 4, 4, 0, 0, 0, 0, 1, 0, 1], "Sample Servicos ME", "SAMPLE SERVICOS ME",
         "Rua Ficticia 789", "Belo Horizonte", "MG", "30130-000", "ATIVA", "VALIDADO"),
        ([4, 4, 5, 5, 5, 0, 0, 0, 0, 1, 0, 1], "QA Solutions EIRELI", "QA SOLUTIONS EIRELI",
         "Rua Qualidade 321", "Curitiba", "PR", "80010-000", "ATIVA", "VALIDADO"),
        ([5, 5, 6, 6, 6, 0, 0, 0, 0, 1, 0, 1], "Teste Automacao LTDA", "TESTE AUTOMACAO LTDA",
         "Av Selenium 654", "Porto Alegre", "RS", "90010-000", "ATIVA", "VALIDADO"),
        ([6, 6, 7, 7, 7, 0, 0, 0, 0, 1, 0, 1], "Ficticio Comercio SA", "FICTICIO COMERCIO SA",
         "Rua Inventada 111", "Salvador", "BA", "40010-000", "BAIXADA", "VALIDADO"),
        ([7, 7, 8, 8, 8, 0, 0, 0, 0, 1, 0, 1], "Exemplo Consultoria ME", "EXEMPLO CONSULTORIA ME",
         "Av Amostra 222", "Recife", "PE", "50010-000", "ATIVA", "VALIDADO"),
        ([8, 8, 9, 9, 9, 0, 0, 0, 0, 1, 0, 1], "Sandbox Digital LTDA", "SANDBOX DIGITAL LTDA",
         "Rua Sandbox 333", "Fortaleza", "CE", "60010-000", "ATIVA", "VALIDADO"),
        ([9, 9, 1, 1, 1, 0, 0, 0, 0, 1, 0, 1], "Alpha Testes SA", "ALPHA TESTES SA",
         "Rua Alpha 444", "Brasilia", "DF", "70010-000", "SUSPENSA", "VALIDADO"),
        ([1, 0, 2, 0, 3, 0, 0, 0, 0, 1, 0, 1], "Beta Software ME", "BETA SOFTWARE ME",
         "Av Beta 555", "Manaus", "AM", "69010-000", "ATIVA", "VALIDADO"),
    ]

    for base_digits, nome_orig, nome_valid, endereco, cidade, estado, cep, situacao, status in empresas:
        cnpj = generate_valid_cnpj(base_digits)
        cursor.execute(
            "INSERT INTO empresas (cnpj, nome_original, nome_validado, endereco, cidade, estado, cep, situacao_cadastral, status_validacao) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (cnpj, nome_orig, nome_valid, endereco, cidade, estado, cep, situacao, status)
        )

    # =============================================
    # Tabela: sintegra (dados por UF ficticios)
    # =============================================
    cursor.execute("""
        CREATE TABLE sintegra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uf TEXT,
            inscricao_estadual TEXT,
            razao_social TEXT,
            situacao TEXT
        )
    """)

    sintegra_data = [
        ("SP", "123456789012", "EMPRESA DEMO SP LTDA", "ATIVA"),
        ("RJ", "234567890123", "TESTE RIO SERVICOS SA", "ATIVA"),
        ("MG", "345678901234", "SAMPLE MINAS COMERCIO ME", "ATIVA"),
        ("PR", "456789012345", "QA PARANA TECH EIRELI", "ATIVA"),
        ("RS", "567890123456", "EXEMPLO SUL DIGITAL LTDA", "BAIXADA"),
    ]

    for uf, ie, razao, situacao in sintegra_data:
        cursor.execute(
            "INSERT INTO sintegra (uf, inscricao_estadual, razao_social, situacao) VALUES (?, ?, ?, ?)",
            (uf, ie, razao, situacao)
        )

    conn.commit()
    conn.close()

    print(f"Banco de dados criado com sucesso em: {db_path}")
    print(f"  - {len(individuos)} individuos (CPFs ficticios)")
    print(f"  - {len(empresas)} empresas (CNPJs ficticios)")
    print(f"  - {len(sintegra_data)} registros SINTEGRA")
    print()
    print("IMPORTANTE: Todos os dados sao FICTICIOS, gerados para demonstracao.")


if __name__ == "__main__":
    create_database()
