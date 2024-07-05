import streamlit as st
from streamlit_option_menu import option_menu
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import tempfile
import openai
import json
import os
import requests
from flask import Flask, request, jsonify
from threading import Thread

# Chave da API OpenAI
openai.api_key = "sk-proj-c4NnmSTgTHNqCD02wO8vT3BlbkFJy1ErZk6BvYcS3LQyuUOl"

# Estrutura para armazenar informações de pull requests
pull_requests = []

# Repository Azure Devops
REPOSITORIO_ESPECIFICO = 'Projeto_code_review'

# Substitua com seu token de acesso pessoal (PAT)
PERSONAL_ACCESS_TOKEN = 'r2tzm72wutcn5fub7yxqtv57o5tl26br35a4zp56xnuwhpxulwya'

# Inicializar o Flask
app = Flask(__name__)

# Configuração do Flask para Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'eventType' in data and data['eventType'] == 'git.pullrequest.created':
        repo_name = data['resource']['repository']['name']
        if repo_name == REPOSITORIO_ESPECIFICO:
            titulo = data['resource']['title']
            descricao = data['resource']['description']
            autor = data['resource']['createdBy']['displayName']
            
            pull_request_url = data['resource']['url']
            changes_url = f"{pull_request_url}/changes"
            
            headers = {
                'Authorization': f'Basic {PERSONAL_ACCESS_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(changes_url, headers=headers)
            if response.status_code == 200:
                changes = response.json()
                pull_request_info = {
                    'titulo': titulo,
                    'descricao': descricao,
                    'autor': autor,
                    'alteracoes': []
                }
                
                for change in changes['value']:
                    file_path = change['item']['path']
                    change_type = change['changeType']
                    lines_added = change.get('linesAdded', 0)
                    lines_deleted = change.get('linesDeleted', 0)
                    
                    pull_request_info['alteracoes'].append({
                        'arquivo': file_path,
                        'tipo': change_type,
                        'linhas_adicionadas': lines_added,
                        'linhas_deletadas': lines_deleted
                    })
                
                pull_requests.append(pull_request_info)
            else:
                print('Erro ao obter as alterações de código:', response.status_code)
        else:
            print(f'Pull request ignorado. Repositório: {repo_name}')
    
    return jsonify({'status': 'received'}), 200

@app.route('/get_pull_requests', methods=['GET'])
def get_pull_requests():
    return jsonify(pull_requests)

# Configuração do Streamlit
def run_streamlit():
    linguagem_1 = "python"
    linguagem_2 = "c++"
    linguagem_3 = "java"

    good_practices = {
        "python": {
            "template": """
            Você é um revisor de código que está auxiliando os desenvolvedores Python.

            A partir das boas práticas de revisão de código, você deve dar um feedback sobre o código desenvolvido.
            Além do feedback, você deve falar se aprovaria o pull request ou não.
            Se não aprovar, é necessário que você diga o porquê e sugira melhorias.

            Sempre no final de cada feedback que você der, precisa falar de forma destacada, se aprovaria a pull request ou não.

            Aqui está o pull request recebido:
            {message}

            Aqui está minha avaliação do pull request do código Python que foi desenvolvido/alterado:
            {best_practice}
            """
        },
        "c++": {
            "template": """
            Você é um revisor de código que está auxiliando os desenvolvedores C++.

            A partir das boas práticas de revisão de código, você deve dar um feedback sobre o código desenvolvido.
            Além do feedback, você deve falar se aprovaria o pull request ou não.
            Se não aprovar, é necessário que você diga o porquê e sugira melhorias.

            Sempre no final de cada feedback que você der, precisa falar de forma destacada, se aprovaria a pull request ou não.

            Aqui está o pull request recebido:
            {message}

            Aqui está minha avaliação do pull request do código C++ que foi desenvolvido/alterado:
            {best_practice}
            """
        },
        "java": {
            "template": """
            Você é um revisor de código que está auxiliando os desenvolvedores Java.

            A partir das boas práticas de revisão de código, você deve dar um feedback sobre o código desenvolvido.
            Além do feedback, você deve falar se aprovaria o pull request ou não.
            Se não aprovar, é necessário que você diga o porquê e sugira melhorias.

            Sempre no final de cada feedback que você der, precisa falar de forma destacada, se aprovaria a pull request ou não.

            Aqui está o pull request recebido:
            {message}

            Aqui está minha avaliação do pull request do código Java que foi desenvolvido/alterado:
            {best_practice}
            """
        }
    }

    def setup_database(file_path):
        loader = TextLoader(file_path)
        documents = loader.load()
        embeddings = OpenAIEmbeddings(openai_api_key=openai.api_key)
        data_base = FAISS.from_documents(documents, embeddings)
        return data_base

    def retrieve_info(query, data_base):
        similar_response = data_base.similarity_search(query, k=3)
        return [doc.page_content for doc in similar_response]

    def setup_llm_chain(language):
        llm = ChatOpenAI(temperature=0.5, model="gpt-4", openai_api_key=openai.api_key)

        template = good_practices[language]["template"]
        
        prompt = PromptTemplate(
            input_variables=["message", "best_practice"],
            template=template
        )

        chain = LLMChain(llm=llm, prompt=prompt)
        return chain

    def generate_response(message, chain, data_base):
        best_practice = retrieve_info(message, data_base)
        response = chain.run(message=message, best_practice=best_practice)
        return response

    def load_history(language):
        history_file = f"chat_history_{language}.json"
        if os.path.exists(history_file):
            with open(history_file, "r") as file:
                return json.load(file)
        return []

    def save_history(language, history):
        history_file = f"chat_history_{language}.json"
        with open(history_file, "w") as file:
            json.dump(history, file)

    def get_pull_requests():
        try:
            response = requests.get("http://localhost:8000/get_pull_requests")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao buscar pull requests: {e}")
            return []

    def get_code_content(url):
        try:
            response = requests.get(url, auth=('', PERSONAL_ACCESS_TOKEN))
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            st.error(f"Erro ao buscar o conteúdo do código: {e}")
            return ""

    st.title("GEN.AI - Treine com seus dados")

    menu = option_menu(
        menu_title=None,
        options=["Python", "C++", "Java"],
        icons=["python", "cplusplus", "java"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )

    submenu = option_menu(
        menu_title=None,
        options=["Treinar Novo Arquivo", "Fazer Perguntas ao Modelo", "Analisar Pull Request do Azure DevOps"],
        icons=["cloud-upload", "question-circle", "cloud"],
        menu_icon="cast",
        default_index=0,
        orientation="horizontal"
    )

    if 'language' not in st.session_state:
        st.session_state.language = None
    if 'data_base' not in st.session_state:
        st.session_state.data_base = None
    if 'llm_chain' not in st.session_state:
        st.session_state.llm_chain = None
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'uploaded_file_path' not in st.session_state:
        st.session_state.uploaded_file_path = None

    if menu in ["Python", "C++", "Java"]:
        language = menu.lower()

        if submenu == "Treinar Novo Arquivo":
            st.header(f"{language.upper()} - Treinar Novo Arquivo")

            if st.session_state.uploaded_file_path:
                st.write(f"Arquivo carregado para treinamento: {st.session_state.uploaded_file_path}")
            else:
                uploaded_file = st.file_uploader("Faça upload de um documento texto para treinamento", type=["txt"])

                if uploaded_file:
                    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        temp_file_path = tmp_file.name

                    st.session_state.uploaded_file_path = temp_file_path
                    st.session_state.data_base = setup_database(temp_file_path)
                    st.session_state.llm_chain = None
                    st.success("Arquivo treinado com sucesso!")

        elif submenu == "Fazer Perguntas ao Modelo":
            st.header(f"{language.upper()} - Fazer Perguntas ao Modelo")
            user_input = st.text_input(f"Pergunte sobre o arquivo texto em {language.upper()}:")

            if user_input:
                if st.session_state.data_base is not None:
                    if st.session_state.llm_chain is None or st.session_state.language != language:
                        st.session_state.llm_chain = setup_llm_chain(language)
                        st.session_state.language = language

                    response = generate_response(user_input, st.session_state.llm_chain, st.session_state.data_base)
                    st.session_state.history.append({"question": user_input, "answer": response})
                    save_history(language, st.session_state.history)
                    st.write("O melhor retorno:")
                    st.write(response)
                else:
                    st.warning("Por favor, treine o modelo com um arquivo antes de fazer perguntas.")

            history = load_history(language)
            if history:
                st.write(f"Histórico da Conversa em {language.upper()}:")
                for entry in history:
                    st.write(f"**Pergunta:** {entry['question']}")
                    st.write(f"**Resposta:** {entry['answer']}")

        elif submenu == "Analisar Pull Request do Azure DevOps":
            st.header(f"{language.upper()} - Analisar Pull Request do Azure DevOps")

            pull_requests = get_pull_requests()

            if pull_requests:
                for pr in pull_requests:
                    with st.expander(f"Pull Request: {pr['titulo']}"):
                        st.write(f"**Descrição:** {pr['descricao']}")
                        st.write(f"**Autor:** {pr['autor']}")
                        st.write("**Alterações:**")
                        for change in pr['alteracoes']:
                            st.write(f"Arquivo: {change['arquivo']}")
                            st.write(f"Tipo: {change['tipo']}")
                            st.write(f"Linhas adicionadas: {change['linhas_adicionada']}")
                            st.write(f"Linhas deletadas: {change['linhas_deletadas']}")
                            st.write("---")
                            
                            if st.button(f"Ver código - {change['arquivo']}"):
                                code_content = get_code_content(change['url'])
                                st.code(code_content, language=language)
            else:
                st.write("Nenhum pull request encontrado")

if __name__ == '__main__':
    flask_thread = Thread(target=lambda: app.run(port=8000, debug=True, use_reloader=False))
    flask_thread.start()
    run_streamlit()
