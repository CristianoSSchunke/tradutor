import streamlit as st
import tradutor
import re

st.set_page_config(page_title="Tradutor KND", page_icon="📢")

# Espaço no topo
st.write("")
st.write("")
st.write("")

col1, col2, col3 = st.columns([1,10,1])

with col2:
    st.markdown("""
     # Tradutor KND 📢
    ## • Quais pedidos vamos traduzir?
    """)
    
    st.write("")
    st.write("")

    mensagem = st.chat_input("Ex: 12345, 67890...")

    if mensagem:
        padrao = r'^[0-9, ]+$'

        if not re.fullmatch(padrao, mensagem):
            st.error("❌ Pedido fora dos padrões (somente números separados por vírgula)")
        
        else:
            erro = tradutor.traduz_pedidos(mensagem)

            if erro:
                st.error(erro)

            else:
                st.success("Pedido Traduzido", icon="✅")
                st.write("Pedidos traduzidos:", mensagem)
