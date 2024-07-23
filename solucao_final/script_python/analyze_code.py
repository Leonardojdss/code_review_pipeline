import requests
import os
import openai
import subprocess
import shutil
import time

# Configurações da OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Configurações do Azure DevOps
DEVOPS_ORG_URL = os.getenv('SYSTEM_COLLECTIONURI')
PROJECT = os.getenv('SYSTEM_TEAMPROJECT')
REPO_ID = os.getenv('BUILD_REPOSITORY_NAME')
PR_ID = os.getenv('SYSTEM_PULLREQUEST_PULLREQUESTID')
SOURCE_COMMIT_ID = os.getenv('SYSTEM_PULLREQUEST_SOURCECOMMITID')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

# Verificação de variáveis de ambiente
required_vars = {
    "SYSTEM_COLLECTIONURI": DEVOPS_ORG_URL,
    "SYSTEM_TEAMPROJECT": PROJECT,
    "BUILD_REPOSITORY_NAME": REPO_ID,
    "SYSTEM_PULLREQUEST_PULLREQUESTID": PR_ID,
    "SYSTEM_PULLREQUEST_SOURCECOMMITID": SOURCE_COMMIT_ID,
    "ACCESS_TOKEN": ACCESS_TOKEN,
    "OPENAI_API_KEY": OPENAI_API_KEY,
}

for var_name, value in required_vars.items():
    if not value:
        raise ValueError(f"A variável de ambiente {var_name} não está definida")

def clone_repo():
    print("Clonando repositório...")
    auth_repo_url = f"https://{ACCESS_TOKEN}@dev.azure.com/leonardojdss01/{PROJECT}/_git/{REPO_ID}"
    repo_dir = "./repo"
    
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

    subprocess.run(["git", "clone", auth_repo_url, repo_dir], check=True)
    os.chdir(repo_dir)
    print("Repositório clonado e diretório acessado.")

def get_commit_content(commit_id):
    print(f"Obtendo conteúdo do commit {commit_id}...")
    result = subprocess.run(["git", "show", commit_id], capture_output=True, text=True, check=True)
    print("Conteúdo do commit obtido.")
    return result.stdout

def analyze_code_with_gpt(file_contents):
    try:
        print("Analisando código com GPT...")
        openai.api_key = OPENAI_API_KEY
        prompt = f"Revise o seguinte código e forneça feedback detalhado:\n{file_contents}"

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": """Você é um assistente que fornece feedback de revisão de código
                        
                        A partir das boas práticas de revisão de código, você deve dar um feedback sobre o código desenvolvido. 
                        Além do feedback, você deve falar se aprovaria o pull request ou não. 
                        Se não aprovar, é necessário que você diga o porquê e sugira melhorias.
                        
                        Sempre no final de cada feedback que você der, precisa falar de forma destacada, se aprovaria a pull request ou não"""
                        }, {"role": "user", "content": prompt}],
            max_tokens=1000
        )
        
        feedback = response.choices[0].message['content']
        print("Análise de código concluída.")
        return feedback
    except Exception as e:
        print(f"Erro ao analisar o código com GPT: {e}")
        return None

def post_feedback_comment(pr_id, feedback, retries=5, wait=5):
    url = f"https://dev.azure.com/leonardojdss01/{PROJECT}/_apis/git/repositories/{REPO_ID}/pullRequests/{pr_id}/threads?api-version=6.0"
    
    curl_command = [
        "curl", "-u", f"leonardojdss01:{ACCESS_TOKEN}",
        "-X", "POST",
        "-H", "Content-Type: application/json",
        "-d", f'{{"comments": [{{"parentCommentId": 0, "content": "{feedback}", "commentType": 1}}], "status": 1}}',
        url
    ]
    
    attempt = 0
    while attempt < retries:
        result = subprocess.run(curl_command, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"Comentário de feedback postado com sucesso na PR {pr_id}.")
            return
        else:
            print(f"Erro ao postar comentário de feedback na PR {pr_id}, tentativa {attempt + 1} de {retries}:")
            print(f"URL: {url}")
            print(f"Status Code: {result.returncode}")
            print(f"Response: {result.stdout}")
            print(f"Error: {result.stderr}")
            attempt += 1
            time.sleep(wait)

    print(f"Falha ao postar comentário de feedback na PR {pr_id} após {retries} tentativas.")

if __name__ == "__main__":
    if not PR_ID:
        print("Nenhum pull request encontrado.")
    else:
        try:
            clone_repo()
            file_contents = get_commit_content(SOURCE_COMMIT_ID)
            if file_contents:
                feedback = analyze_code_with_gpt(file_contents)
                if feedback:
                    post_feedback_comment(PR_ID, feedback)
                else:
                    post_feedback_comment(PR_ID, "Não foi possível trazer uma resposta da IA.")
            else:
                print(f"Conteúdo do commit {SOURCE_COMMIT_ID} não encontrado.")
        except Exception as e:
            print(f"Erro no processamento da PR {PR_ID}: {e}")
            post_feedback_comment(PR_ID, "Não foi possível trazer uma resposta da IA devido a um erro.")
