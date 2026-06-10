"""
QA Agent - Autenticacao para Streamlit
=======================================
Autenticacao basica com usuarios e senhas definidos no .env
"""

import os
import hashlib
from typing import Optional, Dict, Tuple


def get_users() -> Dict[str, str]:
    """Retorna dicionario {usuario: hash_senha} do .env"""
    users_str = os.getenv("STREAMLIT_USERS", "")
    if not users_str:
        return {}
    users = {}
    for entry in users_str.split(","):
        entry = entry.strip()
        if ":" in entry:
            username, password = entry.split(":", 1)
            users[username.strip()] = _hash_password(password.strip())
    return users


def _hash_password(password: str) -> str:
    """Retorna hash SHA-256 da senha"""
    return hashlib.sha256(password.encode()).hexdigest()


def authenticate(username: str, password: str) -> Tuple[bool, str]:
    """
    Autentica usuario.
    Retorna (sucesso, mensagem)
    """
    if not os.getenv("STREAMLIT_AUTH", "false").lower() == "true":
        return True, "Autenticacao desativada"

    users = get_users()
    if not users:
        return True, "Nenhum usuario configurado"

    if username not in users:
        return False, "Usuario ou senha invalidos"

    if users[username] != _hash_password(password):
        return False, "Usuario ou senha invalidos"

    return True, "Autenticado com sucesso"


def login_form() -> Optional[Tuple[str, str]]:
    """
    Renderiza formulario de login.
    Retorna (usuario, senha) se submetido, None caso contrario.
    """
    import streamlit as st

    with st.container():
        st.markdown("## 🔐 QA Agent - Login")
        username = st.text_input("Usuario", key="login_user")
        password = st.text_input("Senha", type="password", key="login_pass")
        if st.button("Entrar", use_container_width=True):
            if username and password:
                return username, password
    return None
