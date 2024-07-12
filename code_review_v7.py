import os
import subprocess
import json
import tempfile
import streamlit as st
from streamlit_option_menu import option_menu
from langchain.document_loaders import TextLoader
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.chains import LLMChain
import openai

# Chave da API OpenAI
openai.api_key = "cole"

# Configurações específicas
linguagem_1 = "python"
linguagem_2 = "c++"
linguagem_3 = "java"
PERSONAL_ACCESS_TOKEN = "cole"
REPOSITORIO_ESPECIFICO = "Projeto_code_review"
REPOSITORIO_URL = "https://dev.azure.com/leonardojdss01/Projeto_code_review/_git/Projeto_code_review"
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
HISTORY_FILE = "pull_requests_history.json"

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

# Função para buscar pull requests usando comandos Git
def fetch_pull_requests():
    try:
        repo_dir = tempfile.mkdtemp()
        
        # Formate a URL com o PAT
        auth_repo_url = REPOSITORIO_URL.replace("https://", f"https://{PERSONAL_ACCESS_TOKEN}@")
        
        # Clonar o repositório
        subprocess.run(["git", "clone", auth_repo_url, repo_dir], check=True)
        
        # Entrar no diretório do repositório
        os.chdir(repo_dir)
        
        # Buscar branches remotas para identificar pull requests
        result = subprocess.run(["git", "ls-remote", "--heads", "origin"], capture_output=True, text=True, check=True)
        
        heads = result.stdout.splitlines()
        pr_branches = [head.split()[1] for head in heads if "refs/heads/" in head]
        
        pull_requests = []
        
        for branch in pr_branches:
            branch_name = branch.strip().split('/')[-1]
            # Obter o código do pull request
            subprocess.run(["git", "fetch", "origin", branch_name], check=True)
            diff_result = subprocess.run(["git", "show", f"origin/{branch_name}"], capture_output=True, text=True, check=True)
            diff_content = diff_result.stdout
            
            pull_requests.append({
                "branch": branch_name,
                "diff": diff_content
            })
        
        return pull_requests
    except subprocess.CalledProcessError as e:
        st.error(f"Erro ao executar comandos git: {e}")
        return []

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

# Função para carregar o histórico das pull requests analisadas
def load_pr_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as file:
            return json.load(file)
    return []

# Função para salvar o histórico das pull requests analisadas
def save_pr_history(history):
    with open(HISTORY_FILE, "w") as file:
        json.dump(history, file)

# Inicializar arquivos de treino carregados na memória
training_files = load_all_training_files()
pr_history = load_pr_history()

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

# Inicializar o estado da sessão para armazenar o arquivo carregado e a cadeia LLM
if "uploaded_file_path" not in st.session_state:
    st.session_state.uploaded_file_path = None

if "llm_chain" not in st.session_state:
    st.session_state.llm_chain = None

if "history" not in st.session_state:
    st.session_state.history = []

# Lógica para o submenu "Treinar Novo Arquivo"
if submenu == "Treinar Novo Arquivo":
    st.header(f"{menu} - Treinar Novo Arquivo")
    uploaded_file = st.file_uploader("Faça upload do arquivo de treino", type=["txt", "pdf", "docx"])
    
    if uploaded_file is not None:
        file_path = save_training_file(uploaded_file)
        st.session_state.uploaded_file_path = file_path
        
        data_base = setup_database(file_path)
        training_files[uploaded_file.name] = data_base
        
        st.success("Arquivo de treino salvo e banco de dados vetorial configurado com sucesso!")

# Lógica para o submenu "Fazer Perguntas ao Modelo"
elif submenu == "Fazer Perguntas ao Modelo":
    st.header(f"{menu} - Fazer Perguntas ao Modelo")
    
    if st.session_state.uploaded_file_path:
        data_base = training_files.get(os.path.basename(st.session_state.uploaded_file_path))
        if data_base:
            st.session_state.llm_chain = setup_llm_chain(menu.lower())
            
            question = st.text_input("Digite sua pergunta")
            if question:
                response = generate_response(question, st.session_state.llm_chain, data_base)
                st.session_state.history.append({"question": question, "answer": response})
                save_history(menu.lower(), st.session_state.history)
        
        for item in st.session_state.history:
            st.write(f"**Pergunta:** {item['question']}")
            st.write(f"**Resposta:** {item['answer']}")
    else:
        st.warning("Por favor, faça upload de um arquivo de treino primeiro.")

# Lógica para o submenu "Analisar Pull Request do Azure DevOps"
elif submenu == "Analisar Pull Request do Azure DevOps":
    st.header(f"{menu} - Analisar Pull Request do Azure DevOps")

    # Botão para buscar novas pull requests
    if st.button("Buscar Pull Requests"):
        pull_requests = fetch_pull_requests()
        if pull_requests:
            st.success(f"{len(pull_requests)} pull requests encontrados.")
        else:
            st.warning("Nenhum pull request encontrado.")

    if pull_requests:
        for pr in pull_requests:
            st.subheader(f"Pull Request: {pr['branch']}")
            st.code(pr['diff'], menu.lower())

            # Botão para analisar a pull request específica
            if st.button(f"Analisar Pull Request {pr['branch']}", key=pr['branch']):
                first_training_file = next(iter(training_files.values()))
                if first_training_file:
                    st.session_state.llm_chain = setup_llm_chain(menu.lower())
                    response = generate_response(pr['diff'], st.session_state.llm_chain, first_training_file)
                    pr_history.append({
                        "branch": pr['branch'],
                        "diff": pr['diff'],
                        "response": response
                    })
                    save_pr_history(pr_history)
                    st.write(f"**Avaliação:** {response}")
                else:
                    st.error("Treine um arquivo e configure a cadeia LLM antes de analisar pull requests.")

        # Mostrar histórico de pull requests analisadas
        if pr_history:
            st.subheader("Histórico de Pull Requests Analisadas")
            for idx, pr in reversed(list(enumerate(pr_history))):
                st.write(f"**Pull Request {idx + 1}:** {pr['branch']}")
                st.code(pr['diff'], menu.lower())
                st.write(f"**Avaliação {idx + 1}:** {pr['response']}")
    else:
        st.write("Nenhum pull request encontrado.")
