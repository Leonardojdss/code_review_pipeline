import streamlit as st
from streamlit_option_menu import option_menu
from langchain_community.document_loaders import TextLoader
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import openai
import json
import os
import subprocess

# Chave da API OpenAI
openai.api_key = "sk-proj-c4NnmSTgTHNqCD02wO8vT3BlbkFJy1ErZk6BvYcS3LQyuUOl"

# Configurações específicas
linguagem_1 = "python"
linguagem_2 = "c++"
linguagem_3 = "java"

# Configurações do Git
GIT_USERNAME = "leonardojdss01"
GIT_PASSWORD = "coleaqui"
ORGANIZATION = "leonardojdss01"
PROJECT = "Projeto_code_review"
REPOSITORY = "Projeto_code_review"
REPO_URL = f"https://{GIT_USERNAME}:{GIT_PASSWORD}@dev.azure.com/{ORGANIZATION}/{PROJECT}/_git/{REPOSITORY}"

pull_requests = []

# Instrução de como a IA deve se comportar
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

# Caminho para o diretório onde os arquivos de treino serão salvos
TRAINING_DIR = "training_files"

# Função para configurar o banco de dados vetorial
def setup_database(file_path):
    loader = TextLoader(file_path)
    documents = loader.load()
    embeddings = OpenAIEmbeddings(openai_api_key=openai.api_key)
    data_base = FAISS.from_documents(documents, embeddings)
    return data_base

# Função para realizar busca nos vetores
def retrieve_info(query, data_base):
    similar_response = data_base.similarity_search(query, k=3)
    return [doc.page_content for doc in similar_response]

# Função para configurar a cadeia LLM
def setup_llm_chain(language):
    llm = ChatOpenAI(temperature=0.5, model="gpt-4", openai_api_key=openai.api_key)

    template = good_practices[language]["template"]
    
    prompt = PromptTemplate(
        input_variables=["message", "best_practice"],
        template=template
    )

    chain = LLMChain(llm=llm, prompt=prompt)
    return chain

# Função para gerar resposta
def generate_response(message, chain, data_base):
    best_practice = retrieve_info(message, data_base)
    response = chain.run(message=message, best_practice=best_practice)
    return response

# Função para carregar o histórico da conversa da linguagem específica
def load_history(language):
    history_file = f"chat_history_{language}.json"
    if os.path.exists(history_file):
        with open(history_file, "r") as file:
            return json.load(file)
    return []

# Função para salvar o histórico da conversa da linguagem específica
def save_history(language, history):
    history_file = f"chat_history_{language}.json"
    with open(history_file, "w") as file:
        json.dump(history, file)

# Função para buscar pull requests usando Git
def get_pull_requests():
    try:
        # Clonar o repositório
        subprocess.run(["git", "clone", REPO_URL], check=True)

        # Mudar para o diretório do repositório clonado
        repo_name = REPOSITORY
        os.chdir(repo_name)

        # Obter lista de pull requests abertas
        result = subprocess.run(["git", "request-pull"], capture_output=True, text=True, check=True)
        pull_requests_output = result.stdout

        # Parsear a saída para obter detalhes das pull requests
        pull_requests = []
        for pr in pull_requests_output.split('request-pull')[1:]:
            pr_info = pr.strip().split('\n')[0]
            pr_title = pr_info.split(':')[0]
            pr_description = pr_info.split(':')[1]
            pull_requests.append({
                "title": pr_title.strip(),
                "description": pr_description.strip(),
                "created_by": "N/A",  # A saída do comando Git não inclui o autor
                "changes_url": f"{REPO_URL}/pull/{pr_title.strip()}"
            })

        # Voltar para o diretório original
        os.chdir('..')

        return pull_requests
    except subprocess.CalledProcessError as e:
        st.error(f"Erro ao buscar pull requests: {e}")
        return []

# Função para carregar o conteúdo do código das alterações
def get_code_content(url):
    try:
        result = subprocess.run(["git", "show", url], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        st.error(f"Erro ao buscar o conteúdo do código: {e}")
        return ""

# Função para carregar todos os arquivos de treino e seus bancos de dados vetoriais
def load_all_training_files():
    if not os.path.exists(TRAINING_DIR):
        os.makedirs(TRAINING_DIR)
    
    training_files = {}
    for filename in os.listdir(TRAINING_DIR):
        file_path = os.path.join(TRAINING_DIR, filename)
        data_base = setup_database(file_path)
        training_files[filename] = data_base
    
    return training_files

# Função para salvar um novo arquivo de treino
def save_training_file(file):
    file_path = os.path.join(TRAINING_DIR, file.name)
    with open(file_path, "wb") as f:
        f.write(file.getvalue())
    return file_path

# Inicializar arquivos de treino carregados na memória
training_files = load_all_training_files()

# Configuração do Streamlit
st.title("GEN.AI - Treine com seus dados")

# Menu de navegação flutuante na parte superior
menu = option_menu(
    menu_title=None,
    options=["Python", "C++", "Java"],
    icons=["python", "cplusplus", "java"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal"
)

# Submenu para cada linguagem
submenu = option_menu(
    menu_title=None,
    options=["Treinar Novo Arquivo", "Fazer Perguntas ao Modelo", "Analisar Pull Request do Azure DevOps"],
    icons=["cloud-upload", "question-circle", "cloud"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal"
)

# Inicializar o estado da sessão do Streamlit
if "history" not in st.session_state:
    st.session_state.history = {
        "python": [],
        "c++": [],
        "java": []
    }

if "code_analysis_history" not in st.session_state:
    st.session_state.code_analysis_history = []

if "llm_chain" not in st.session_state:
    st.session_state.llm_chain = None

if "uploaded_file_path" not in st.session_state:
    st.session_state.uploaded_file_path = None

language = menu.lower()

if submenu == "Treinar Novo Arquivo":
    st.header(f"{language.upper()} - Treinar Novo Arquivo")

    if st.session_state.uploaded_file_path:
        st.write(f"Arquivo carregado para treinamento: {st.session_state.uploaded_file_path}")
    else:
        uploaded_file = st.file_uploader("Faça upload de um documento texto para treinamento", type=["txt"])

        if uploaded_file:
            file_path = save_training_file(uploaded_file)
            training_files[uploaded_file.name] = setup_database(file_path)
            st.session_state.uploaded_file_path = file_path
            st.session_state.llm_chain = None  # Resetar a cadeia LLM ao treinar novo arquivo
            st.success("Arquivo treinado com sucesso!")

elif submenu == "Fazer Perguntas ao Modelo":
    st.header(f"{language.upper()} - Fazer Perguntas ao Modelo")

    if training_files:
        if not st.session_state.llm_chain:
            st.session_state.llm_chain = setup_llm_chain(language)

        st.subheader("Analisar Arquivo TXT")
        uploaded_txt_file = st.file_uploader("Faça upload de um arquivo de código (TXT)", type=["txt"])

        if uploaded_txt_file:
            txt_content = uploaded_txt_file.getvalue().decode("utf-8")
            st.text_area("Conteúdo do Arquivo:", txt_content, height=300)

            if st.button("Analisar Código"):
                first_training_file = next(iter(training_files.values()))
                response = generate_response(txt_content, st.session_state.llm_chain, first_training_file)
                st.session_state.code_analysis_history.append({"codigo": txt_content, "resposta": response})
                st.write(f"**Avaliação do Código:** {response}")

        if st.session_state.code_analysis_history:
            st.subheader("Histórico de Análise de Código")
            for idx, analysis in reversed(list(enumerate(st.session_state.code_analysis_history))):
                st.write(f"**Código Analisado {idx + 1}:**")
                st.text_area(f"Código {idx + 1}", analysis["codigo"], height=300)
                st.write(f"**Resposta {idx + 1}:** {analysis['resposta']}")

        user_input = st.text_input("Digite sua pergunta:")

        if user_input:
            first_training_file = next(iter(training_files.values()))
            response = generate_response(user_input, st.session_state.llm_chain, first_training_file)
            st.session_state.history.append({"pergunta": user_input, "resposta": response})
            save_history(language, st.session_state.history)

        st.subheader("Histórico da Conversa")
        for idx, chat in reversed(list(enumerate(st.session_state.history))):
            st.write(f"**Pergunta {idx + 1}:** {chat['pergunta']}")
            st.write(f"**Resposta {idx + 1}:** {chat['resposta']}")

    else:
        st.warning("Nenhum arquivo de treino carregado. Por favor, carregue um arquivo no menu 'Treinar Novo Arquivo'.")

elif submenu == "Analisar Pull Request do Azure DevOps":
    st.header(f"{language.upper()} - Analisar Pull Request do Azure DevOps")

    if st.button("Buscar Pull Requests"):
        pull_requests = get_pull_requests()

    if pull_requests:
        for pr in pull_requests:
            st.subheader(f"Pull Request: {pr['title']}")
            st.write(f"Descrição: {pr['description']}")
            st.write(f"Autor: {pr['created_by']}")

            code_content = get_code_content(pr['changes_url'])
            st.code(code_content, language)

            if st.button(f"Analisar Pull Request #{pr['title']}"):
                first_training_file = next(iter(training_files.values()))
                response = generate_response(code_content, st.session_state.llm_chain, first_training_file)
                st.session_state.code_analysis_history.append({"codigo": code_content, "resposta": response})
                st.write(f"**Avaliação:** {response}")
    else:
        st.write("Nenhum pull request encontrado.")
