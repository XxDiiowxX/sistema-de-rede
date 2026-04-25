import streamlit as st
import sqlite3
import pandas as pd
import requests # Biblioteca para conectar com APIs externas no futuro

st.set_page_config(page_title="Cadastro na Rede", page_icon="🌳", layout="centered")

# =====================================================================
# 1. CONFIGURAÇÃO DO BANCO DE DADOS
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
    # Adicionando a coluna de validação sem quebrar o banco antigo
    try: cursor.execute("ALTER TABLE usuarios ADD COLUMN whatsapp_validado INTEGER DEFAULT 0")
    except: pass
    
    conexao.commit()
    return conexao

conexao = conectar_banco()

# =====================================================================
# 2. ROTA DE VALIDAÇÃO DO WHATSAPP (Interceptador)
# =====================================================================
# Se o usuário clicar no link enviado no WhatsApp (ex: seusite.com/?validar=62999999999)
# O sistema cai aqui, atualiza o banco e para.
if "validar" in st.query_params:
    celular_alvo = st.query_params["validar"]
    cursor = conexao.cursor()
    cursor.execute("UPDATE usuarios SET whatsapp_validado = 1 WHERE celular = ?", (celular_alvo,))
    conexao.commit()
    st.title("✅ WhatsApp Validado!")
    st.success("Seu número foi confirmado com sucesso na nossa rede. Você já pode fechar esta tela.")
    st.balloons()
    st.stop() # Interrompe o código aqui para não mostrar o resto do site

# =====================================================================
# FUNÇÃO GATILHO PARA A API DE WHATSAPP (Aguardando sua API)
# =====================================================================
import requests

def enviar_mensagem_whatsapp(nome, celular):
    # DADOS DA SUA API ULTRAMSG (Lidos da sua tela!)
    INSTANCIA = "instance171844"
    TOKEN = "ept4dfanq3mszasp"
    
    # O link que o usuário clicará para validar o cadastro
    link_validacao = f"http://localhost:8501/?validar={celular}"
    
    mensagem = (
        f"Olá, *{nome.title()}*! ✨\n\n"
        f"Recebemos o seu cadastro na nossa rede oficial.\n"
        f"Para confirmar que este número é seu e ativar o seu link de indicação, "
        f"clique no link abaixo:\n\n"
        f"👉 {link_validacao}\n\n"
        f"_Se não foi você que solicitou, ignore esta mensagem._"
    )
    
    url = f"https://api.ultramsg.com/{INSTANCIA}/messages/chat"
    
    payload = {
        "token": TOKEN,
        "to": f"+55{celular}", # O +55 garante que o WhatsApp entenda que é no Brasil
        "body": mensagem
    }
    
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    
    try:
        # O Python faz a chamada para a UltraMsg e ela dispara o WhatsApp
        response = requests.post(url, data=payload, headers=headers)
        # Imprime no terminal preto do VS Code para você monitorar se deu certo
        print(f"Status do disparo para {celular}: {response.text}") 
        return response.json()
    except Exception as e:
        print(f"Erro no disparo: {e}")
        return None


# =====================================================================
# 3. LOGIN E CONTROLE DE SESSÃO
# =====================================================================
if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = None
if 'perfil_acesso' not in st.session_state: st.session_state.perfil_acesso = None

with st.sidebar:
    if st.session_state.usuario_logado is None:
        st.header("🔐 Acesso Restrito")
        login_nome = st.text_input("Usuário (Nome)").lower().strip()
        login_senha = st.text_input("Senha", type="password")
        
        if st.button("Entrar no Sistema", use_container_width=True):
            if login_nome == "admin" and login_senha == "admin":
                st.session_state.usuario_logado = "Admin Master"
                st.session_state.perfil_acesso = "admin"
                st.rerun()
            else:
                df_login = pd.read_sql(f"SELECT * FROM usuarios WHERE nome = '{login_nome}' AND senha = '{login_senha}' AND acesso_liberado = 1", conexao)
                if not df_login.empty:
                    st.session_state.usuario_logado = login_nome
                    st.session_state.perfil_acesso = "lider"
                    st.rerun()
                else:
                    st.error("Credenciais incorretas ou acesso não liberado.")
    else:
        st.success(f"Logado como: **{st.session_state.usuario_logado.title()}**")
        if st.button("Sair (Logout)", use_container_width=True):
            st.session_state.usuario_logado = None
            st.session_state.perfil_acesso = None
            st.rerun()

# =====================================================================
# MATEMÁTICA E LÓGICA DE BOLHA
# =====================================================================
df_rede = pd.read_sql("SELECT * FROM usuarios", conexao)
nomes_cadastrados = ["nenhum"]

if not df_rede.empty:
    df_rede['nome'] = df_rede['nome'].str.lower().str.strip()
    df_rede['patrocinador'] = df_rede['patrocinador'].str.lower().str.strip()
    nomes_cadastrados.extend(df_rede['nome'].tolist())

    def contar_downline(nome_alvo, df):
        total = 0
        filhos = df[df['patrocinador'] == nome_alvo]['nome'].tolist()
        for filho in filhos:
            total += 1
            total += contar_downline(filho, df)
        return total

    df_rede['Tamanho da Equipe'] = df_rede['nome'].apply(lambda x: contar_downline(x, df_rede))

def obter_toda_downline(nome_alvo, df):
    descendentes = []
    filhos = df[df['patrocinador'] == nome_alvo]['nome'].tolist()
    for filho in filhos:
        descendentes.append(filho)
        descendentes.extend(obter_toda_downline(filho, df))
    return descendentes

def desenhar_arvore_visual(nome_atual, df, nivel=0):
    linha = df[df['nome'] == nome_atual].iloc[0]
    tamanho = linha['Tamanho da Equipe']
    tag = linha['tag_admin']
    # Checa se validou para colocar o ícone verde ou vermelho
    validado = "✅" if linha['whatsapp_validado'] == 1 else "⚠️"
    
    espacamento = "&nbsp;" * (nivel * 12)
    simbolo = "↳" if nivel > 0 else "📍"
    cor_destaque = "green" if nivel == 0 else "gray"
    texto_tag = f" <span style='color:blue; font-size:14px;'>[{tag}]</span>" if tag else ""
    
    st.markdown(f"{espacamento} {simbolo} <strong style='color:{cor_destaque}; font-size:18px;'>{nome_atual.title()}</strong> {validado} <span style='color:gray;'>(Rede: {tamanho})</span>{texto_tag}", unsafe_allow_html=True)
    
    filhos = df[df['patrocinador'] == nome_atual]['nome'].tolist()
    for filho in filhos:
        desenhar_arvore_visual(filho, df, nivel + 1)

# =====================================================================
# ROTEADOR DE TELAS
# =====================================================================

# CENÁRIO 1: O FUNIL PÚBLICO
if st.session_state.usuario_logado is None:
    parametros_url = st.query_params
    patrocinador_indicado = parametros_url.get("ref", "nenhum").lower()

    st.title("🌳 Faça parte da Rede")
    st.write("Preencha seus dados abaixo para gerar o seu link exclusivo de indicação.")

    with st.form("form_cadastro"):
        nome_novo = st.text_input("Seu Nome (Ex: marcelo_silva)")
        celular_input = st.text_input("Seu WhatsApp (Somente números, com DDD)")
        
        if patrocinador_indicado != "nenhum" and patrocinador_indicado in nomes_cadastrados:
            indice = nomes_cadastrados.index(patrocinador_indicado)
            patrocinador = st.selectbox("Quem indicou?", nomes_cadastrados, index=indice, disabled=True)
        else:
            patrocinador = st.selectbox("Quem indicou? (Escolha na lista)", nomes_cadastrados)
        
        if st.form_submit_button("Cadastrar e Gerar Meu Link", use_container_width=True):
            
            # A TRAVA DE 11 DÍGITOS
            celular_limpo = "".join(c for c in celular_input if c.isdigit())
            
            if not nome_novo or not celular_limpo:
                st.warning("Preencha o nome e o celular!")
            elif len(celular_limpo) != 11:
                st.error("❌ O número deve ter exatamente 11 dígitos (2 do DDD + 9 do número). Ex: 62999999999")
            else:
                nome_novo = nome_novo.lower().strip()
                try:
                    cursor = conexao.cursor()
                    cursor.execute("INSERT INTO usuarios (nome, celular, patrocinador) VALUES (?, ?, ?)", 
                                   (nome_novo, celular_limpo, patrocinador))
                    conexao.commit()
                    
                    # Chama a função de disparo de WhatsApp (Simulada por enquanto)
                    enviar_mensagem_whatsapp(nome_novo, celular_limpo)
                    
                    link_gerado = f"http://localhost:8501/?ref={nome_novo}"
                    st.success("✅ Cadastro realizado com sucesso!")
                    st.info(f"Seu link para enviar no WhatsApp: **{link_gerado}**")
                    
                    # Mensagem sobre a validação
                    st.warning(f"Mandamos um link de confirmação para o WhatsApp **{celular_limpo}**. Clique nele para validar sua conta na rede!")
                    
                except sqlite3.IntegrityError:
                    st.error("❌ Esse nome já existe na rede. Escolha outro.")

    with st.expander("🔗 Já é cadastrado? Pegue seu link de indicação aqui"):
        nome_busca = st.text_input("Qual o seu nome cadastrado?", key="busca_nome")
        if st.button("Buscar Link"):
            nome_busca_limpo = nome_busca.lower().strip()
            if nome_busca_limpo in nomes_cadastrados and nome_busca_limpo != "nenhum":
                link_recuperado = f"http://localhost:8501/?ref={nome_busca_limpo}"
                st.success("Usuário encontrado!")
                st.code(link_recuperado, language="http")
            elif nome_busca_limpo != "":
                st.error("❌ Nome não encontrado.")

# CENÁRIO 2: DASHBOARD DO LÍDER (Micro-SaaS Gamificado)
elif st.session_state.perfil_acesso == "lider":
    lider = st.session_state.usuario_logado
    st.title("📊 Painel do Líder")
    st.code(f"http://localhost:8501/?ref={lider}", language="http")
    st.divider()

    descendentes = obter_toda_downline(lider, df_rede)
    df_equipe = df_rede[df_rede['nome'].isin(descendentes)]

    aba1, aba2, aba3 = st.tabs(["🌳 Sua Árvore", "🏆 Ranking & Base", "🏷️ Organizar Equipe"])

    with aba1:
        st.write("Visualização da sua estrutura de indicados. (✅ = WhatsApp Validado / ⚠️ = Não Validado)")
        desenhar_arvore_visual(lider, df_rede)

    with aba2:
        st.subheader("🏆 Top 10 Recrutadores da Sua Equipe")
        if not df_equipe.empty and (df_equipe['Tamanho da Equipe'] > 0).any():
            df_top = df_equipe[df_equipe['Tamanho da Equipe'] > 0].nlargest(10, 'Tamanho da Equipe')
            st.bar_chart(df_top.set_index('nome')[['Tamanho da Equipe']], color="#2e8b57")
        else:
            st.info("Ainda não há recrutadores na sua base para gerar o ranking.")
            
        st.subheader("📋 Lista de Contatos")
        if not df_equipe.empty:
            # Mostrando quem está validado na tabela também
            st.dataframe(df_equipe[['nome', 'celular', 'whatsapp_validado', 'Tamanho da Equipe', 'tag_admin']], use_container_width=True, hide_index=True)
        else:
            st.write("Você ainda não possui indicados.")

    with aba3:
        st.subheader("🏷️ Defina Tags para seus Indicados")
        if not df_equipe.empty:
            col1, col2 = st.columns(2)
            with col1:
                user_alvo = st.selectbox("Selecione o contato da sua equipe:", df_equipe['nome'].tolist())
            with col2:
                nova_tag = st.text_input("Digite a Tag (Ex: Coordenador de Bairro):")
                
            if st.button("Salvar Tag da Equipe"):
                cursor = conexao.cursor()
                cursor.execute("UPDATE usuarios SET tag_admin = ? WHERE nome = ?", (nova_tag, user_alvo))
                conexao.commit()
                st.success(f"Tag atualizada para {user_alvo.title()}!")
                st.rerun()
        else:
            st.info("Você precisa ter indicados para usar o sistema de tags.")

# CENÁRIO 3: DASHBOARD DO ADMIN GERAL
elif st.session_state.perfil_acesso == "admin":
    st.title("👑 Painel de Controle Master")
    
    if df_rede.empty:
        st.write("Base vazia.")
    else:
        aba1, aba2, aba3, aba4 = st.tabs(["🏆 Ranking Global", "🌳 Árvore Completa", "🏷️ Tags Master", "🔑 Acessos"])
        
        with aba1:
            st.subheader("🚀 Top 10 Maiores Líderes da Rede")
            if (df_rede['Tamanho da Equipe'] > 0).any():
                df_top_global = df_rede[df_rede['Tamanho da Equipe'] > 0].nlargest(10, 'Tamanho da Equipe')
                st.bar_chart(df_top_global.set_index('nome')[['Tamanho da Equipe']], color="#005b96")
            else:
                st.write("Ninguém iniciou o recrutamento ainda.")
                
            st.subheader("📋 Base de Dados Bruta (✅1 = Validado / 0 = Não Validado)")
            st.dataframe(df_rede[['id', 'nome', 'celular', 'whatsapp_validado', 'patrocinador', 'Tamanho da Equipe', 'tag_admin']], use_container_width=True, hide_index=True)
            
        with aba2:
            st.write("Hierarquia global de todos os cadastros. (✅ = WhatsApp Validado / ⚠️ = Não Validado)")
            raizes = df_rede[(df_rede['patrocinador'] == 'nenhum') | (df_rede['patrocinador'] == '')]['nome'].tolist()
            for raiz in raizes:
                desenhar_arvore_visual(raiz, df_rede)
                st.write("")
                
        with aba3:
            st.markdown("**Adicione Tags administrativas para qualquer contato da rede:**")
            col1, col2 = st.columns(2)
            with col1:
                user_alvo = st.selectbox("Selecione o contato:", df_rede['nome'].tolist())
            with col2:
                nova_tag = st.text_input("Digite a Tag:")
                
            if st.button("Salvar Tag Global"):
                cursor = conexao.cursor()
                cursor.execute("UPDATE usuarios SET tag_admin = ? WHERE nome = ?", (nova_tag, user_alvo))
                conexao.commit()
                st.success("Tag salva com sucesso!")
                st.rerun()

        with aba4:
            st.markdown("**Libere acesso ao painel para seus líderes.**")
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                user_alvo_senha = st.selectbox("Selecione o Líder:", df_rede['nome'].tolist(), key="select_senha")
            with col2:
                nova_senha = st.text_input("Defina a senha de acesso:")
            with col3:
                st.write("")
                st.write("")
                liberar = st.checkbox("Liberar Acesso")
            
            if st.button("Salvar Permissões", type="primary"):
                status_acesso = 1 if liberar else 0
                cursor = conexao.cursor()
                cursor.execute("UPDATE usuarios SET senha = ?, acesso_liberado = ? WHERE nome = ?", (nova_senha, status_acesso, user_alvo_senha))
                conexao.commit()
                st.success(f"Permissões atualizadas para {user_alvo_senha.title()}!")
                st.rerun()
