import streamlit as st
import sqlite3
import pandas as pd
import requests

# CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Cadastro na Rede", page_icon="🌳", layout="centered")

# LINK ATUALIZADO (Conforme o seu último print do Streamlit Cloud)
SITE_OFICIAL = "https://sistema-de-rede-2vvkd27b3neay6evluwrdw.streamlit.app"

# =====================================================================
# 1. BANCO DE DADOS
# =====================================================================
def conectar_banco():
    conexao = sqlite3.connect('rede_oficial.db')
    cursor = conexao.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            celular TEXT NOT NULL,
            patrocinador TEXT,
            tag_admin TEXT DEFAULT '',
            senha TEXT DEFAULT '',
            acesso_liberado INTEGER DEFAULT 0,
            whatsapp_validado INTEGER DEFAULT 0
        )
    ''')
    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN tag_admin TEXT DEFAULT ''")
    except: pass
    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN senha TEXT DEFAULT ''")
    except: pass
    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN acesso_liberado INTEGER DEFAULT 0")
    except: pass
    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN whatsapp_validado INTEGER DEFAULT 0")
    except: pass
    
    conexao.commit()
    return conexao

conexao = conectar_banco()

# =====================================================================
# 2. SISTEMA DE DISPARO WHATSAPP (ULTRAMSG)
# =====================================================================
def enviar_mensagem_whatsapp(nome, celular):
    INSTANCIA = "instance171844"
    TOKEN = "ept4dfanq3mszasp"
    
    link_validacao = f"{SITE_OFICIAL}/?validar={celular}"
    
    mensagem = (
        f"Olá, *{nome.title()}*! ✨\n\n"
        f"Recebemos o seu cadastro na nossa rede oficial.\n"
        f"Para confirmar seu número e ativar seu link de indicação, clique abaixo:\n\n"
        f"👉 {link_validacao}\n\n"
        f"_Se não foi você, ignore esta mensagem._"
    )
    
    url = f"https://api.ultramsg.com/{INSTANCIA}/messages/chat"
    payload = {"token": TOKEN, "to": f"+55{celular}", "body": mensagem}
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    
    try:
        requests.post(url, data=payload, headers=headers)
    except:
        pass

# =====================================================================
# 3. INTERCEPTADOR DE VALIDAÇÃO
# =====================================================================
if "validar" in st.query_params:
    celular_alvo = st.query_params["validar"]
    cursor = conexao.cursor()
    cursor.execute("UPDATE usuarios SET whatsapp_validado = 1 WHERE celular = ?", (celular_alvo,))
    conexao.commit()
    st.title("✅ WhatsApp Validado!")
    st.success("Seu número foi confirmado! Você já pode fechar esta tela.")
    st.balloons()
    st.stop()

# =====================================================================
# 4. CONTROLE DE SESSÃO E LOGIN
# =====================================================================
if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
if 'perfil_acesso' not in st.session_state: st.session_state.perfil_acesso = None

with st.sidebar:
    if st.session_state.usuario_logado is None:
        st.header("🔐 Área do Líder")
        l_nome = st.text_input("Usuário").lower().strip()
        l_senha = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            if l_nome == "admin" and l_senha == "admin":
                st.session_state.usuario_logado, st.session_state.perfil_acesso = "Admin Master", "admin"
                st.rerun()
            else:
                df_l = pd.read_sql(f"SELECT * FROM usuarios WHERE nome='{l_nome}' AND senha='{l_senha}' AND acesso_liberado=1", conexao)
                if not df_l.empty:
                    st.session_state.usuario_logado, st.session_state.perfil_acesso = l_nome, "lider"
                    st.rerun()
                else: st.error("Acesso negado.")
    else:
        st.write(f"Logado: **{st.session_state.usuario_logado.title()}**")
        if st.button("Sair"):
            st.session_state.usuario_logado = st.session_state.perfil_acesso = None
            st.rerun()

# =====================================================================
# 5. MATEMÁTICA DA REDE
# =====================================================================
df_rede = pd.read_sql("SELECT * FROM usuarios", conexao)
nomes_cadastrados = ["nenhum"]

if not df_rede.empty:
    df_rede['nome'] = df_rede['nome'].str.lower().str.strip()
    df_rede['patrocinador'] = df_rede['patrocinador'].str.lower().str.strip()
    nomes_cadastrados.extend(df_rede['nome'].tolist())

    def contar_downline(nome_alvo, df):
        filhos = df[df['patrocinador'] == nome_alvo]['nome'].tolist()
        return len(filhos) + sum(contar_downline(f, df) for f in filhos)

    df_rede['Tamanho da Equipe'] = df_rede['nome'].apply(lambda x: contar_downline(x, df_rede))

def obter_toda_downline(nome_alvo, df):
    descendentes = []
    filhos = df[df['patrocinador'] == nome_alvo]['nome'].tolist()
    for f in filhos:
        descendentes.append(f)
        descendentes.extend(obter_toda_downline(f, df))
    return descendentes

def desenhar_arvore(nome_atual, df, nivel=0):
    lin = df[df['nome'] == nome_atual].iloc[0]
    val = "✅" if lin['whatsapp_validado'] == 1 else "⚠️"
    tag = f" <span style='color:blue;'>[{lin['tag_admin']}]</span>" if lin['tag_admin'] else ""
    st.markdown(f"{'&nbsp;'*(nivel*12)} {'↳' if nivel>0 else '📍'} **{nome_atual.title()}** {val} (Rede: {lin['Tamanho da Equipe']}){tag}", unsafe_allow_html=True)
    for f in df[df['patrocinador'] == nome_atual]['nome'].tolist():
        desenhar_arvore(f, df, nivel + 1)

# =====================================================================
# 6. TELAS (ROTEADOR)
# =====================================================================

if st.session_state.usuario_logado is None:
    st.title("🌳 Faça parte da Rede")
    ref_url = st.query_params.get("ref", "nenhum").lower()
    
    with st.form("cadastro"):
        n = st.text_input("Seu Nome (sem espaços)").lower().strip()
        c = st.text_input("WhatsApp (DDD + Número)")
        p = st.selectbox("Quem indicou?", nomes_cadastrados, index=nomes_cadastrados.index(ref_url) if ref_url in nomes_cadastrados else 0)
        
        if st.form_submit_button("Cadastrar e Gerar Link", use_container_width=True):
            c_clean = "".join(filter(str.isdigit, c))
            if n and len(c_clean) == 11:
                try:
                    cursor = conexao.cursor()
                    cursor.execute("INSERT INTO usuarios (nome, celular, patrocinador) VALUES (?,?,?)", (n, c_clean, p))
                    conexao.commit()
                    enviar_mensagem_whatsapp(n, c_clean)
                    st.success(f"✅ Cadastro de {n.title()} realizado!")
                    st.info("📢 **COPIE SEU LINK DE INDICAÇÃO ABAIXO:**")
                    st.code(f"{SITE_OFICIAL}/?ref={n}")
                    st.warning("Confirme o link enviado no seu WhatsApp para validar seu número!")
                except: st.error("Nome já existe na rede.")
            else: st.error("WhatsApp precisa de 11 dígitos (DDD+Número).")

    with st.expander("🔗 Recuperar meu link"):
        b = st.text_input("Seu nome cadastrado").lower().strip()
        if st.button("Buscar Link"):
            if b in nomes_cadastrados: st.code(f"{SITE_OFICIAL}/?ref={b}")
            else: st.error("Usuário não encontrado.")

elif st.session_state.perfil_acesso == "lider":
    u = st.session_state.usuario_logado
    st.title(f"📊 Painel: {u.title()}")
    st.info(f"Seu Link de Convite: {SITE_OFICIAL}/?ref={u}")
    
    aba1, aba2, aba3 = st.tabs(["🌳 Minha Rede", "🏆 Ranking", "🏷️ Organizar"])
    down = obter_toda_downline(u, df_rede)
    df_e = df_rede[df_rede['nome'].isin(down)]
    
    with aba1: desenhar_arvore(u, df_rede)
    with aba2:
        if not df_e.empty:
            st.bar_chart(df_e.nlargest(10, 'Tamanho da Equipe').set_index('nome')['Tamanho da Equipe'])
            st.dataframe(df_e[['nome', 'celular', 'whatsapp_validado', 'Tamanho da Equipe', 'tag_admin']], use_container_width=True)
    with aba3:
        if not df_e.empty:
            alvo = st.selectbox("Membro da Equipe:", df_e['nome'].tolist())
            t = st.text_input("Nova Tag Administrativa:")
            if st.button("Salvar Tag"):
                cursor = conexao.cursor()
                cursor.execute("UPDATE usuarios SET tag_admin=? WHERE nome=?", (t, alvo))
                conexao.commit()
                st.rerun()

elif st.session_state.perfil_acesso == "admin":
    st.title("👑 Admin Master")
    aba1, aba2, aba3 = st.tabs(["🏆 Global", "🌳 Árvore Completa", "🔑 Acessos"])
    with aba1: st.dataframe(df_rede, use_container_width=True)
    with aba2:
        raizes = df_rede[df_rede['patrocinador'].isin(['nenhum', ''])]['nome'].tolist()
        for r in raizes:
            desenhar_arvore(r, df_rede)
            st.write("---")
    with aba3:
        alvo = st.selectbox("Selecione o Líder:", df_rede['nome'].tolist())
        sen = st.text_input("Definir Senha:")
        lib = st.checkbox("Liberar Login no Painel")
        if st.button("Atualizar Permissões"):
            cursor = conexao.cursor()
            cursor.execute("UPDATE usuarios SET senha=?, acesso_liberado=? WHERE nome=?", (sen, 1 if lib else 0, alvo))
            conexao.commit()
            st.success("Configurações de acesso atualizadas!")
            st.rerun()
