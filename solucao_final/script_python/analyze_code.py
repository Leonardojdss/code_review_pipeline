import requests
import os
import openai
import subprocess
import shutil
import time

# Configurações da Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = os.getenv('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')

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
    "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
    "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
    "AZURE_OPENAI_DEPLOYMENT_NAME": AZURE_OPENAI_DEPLOYMENT_NAME,
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
        openai.api_type = "azure"
        openai.api_base = AZURE_OPENAI_ENDPOINT
        openai.api_version = "2023-05-15"  # Verifique a versão da API
        openai.api_key = AZURE_OPENAI_API_KEY
        
        prompt = f"""Revise o seguinte código e forneça feedback detalhado, considere todas as instruções inseridas na mensagem do "system", "content": e Considere as linhas marcadas como '- ' e '+ ' para identificar as mudanças feitas:\n\n{file_contents}"""

        response = openai.ChatCompletion.create(
            deployment_id=AZURE_OPENAI_DEPLOYMENT_NAME,
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """
                    
                    Você está revisando uma pull request de um projeto que utiliza boas práticas de desenvolvimento.\n
                    \n
                    **Tarefas**:\n
                    \n
                    **1.Feedback**: Com base nas boas práticas de revisão de código, forneça um feedback detalhado sobre o código desenvolvido. Estruture seu feedback nas seguintes seções:\n
                    \n
                    **1.1 Pontos Fortes**: Destaque os aspectos positivos do código, mencionando especificamente as partes relevantes.\n
                        Inclua exemplos específicos do código como pontos fortes.\n
                    **1.2 Problemas Identificados**: Liste e explique os problemas encontrados, referenciando as linhas de código problemáticas.\n
                        Se houver qualquer problema, a pull request não pode ser aprovada, então seu feedback deve indicar reprovação.\n
                    Inclua exemplos específicos do código como problemas.\n
                    **1.3 Sugestões de Melhoria:** Sugira melhorias específicas para cada problema identificado, indicando como o código pode ser ajustado.\n
                        Inclua exemplos de código demonstrando as melhorias sugeridas.\n
                    \n
                    **2.Aprovação da Pull Request:** Avalie se você aprovaria a pull request ou não.\n
                        Se Aprovar: Use a frase: "Eu aprovaria esta pull request, pois minha revisão não identificou problemas."\n
                            Se houver qualquer problema, a pull request não pode ser aprovada, então seu feedback deve indicar reprovação.\n 
                        Se Não Aprovar: Use a frase: "Eu não aprovaria esta pull request por conta dos problemas identificados acima."\n
                    \n
                    **3.Pontuação:** Sempre pontue o código de 0 a 10, onde 0 é muito ruim e 10 é excelente.\n
                        Cada Problemas identificado deve ser subtraido 1 pontos

                    Lembre-se de fornecer uma análise detalhada e objetiva."""},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )

        feedback = response.choices[0].message['content']
        print("Análise de código concluída.")
        return feedback
    except Exception as e:
        print(f"Erro ao analisar o código com GPT: {e}")
        return None

def post_feedback_comment(pr_id, feedback, retries=10, wait=2):
    url = f"https://dev.azure.com/leonardojdss01/{PROJECT}/_apis/git/repositories/{REPO_ID}/pullRequests/{pr_id}/threads?api-version=6.0"
    headers = {
        "Content-Type": "application/json"
    }
    auth = ("leonardojdss01", ACCESS_TOKEN)
    data = {
        "comments": [
            {
                "parentCommentId": 0,
                "content": feedback,
                "commentType": 1
            }
        ],
        "status": 1
    }
    
    attempt = 0
    while attempt < retries:
        response = requests.post(url, json=data, headers=headers, auth=auth)
        
        if response.status_code == 200:
            print(f"Comentário de feedback postado com sucesso na PR {pr_id}.")
            return
        else:
            print(f"Erro ao postar comentário de feedback na PR {pr_id}, tentativa {attempt + 1} de {retries}:")
            print(f"URL: {url}")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
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
            print(f"Conteúdo do commit:\n{file_contents}")  # Adicionado para verificar o conteúdo do commit
            if file_contents:
                feedback = analyze_code_with_gpt(file_contents)
                print(f"Feedback gerado:\n{feedback}")  # Adicionado para verificar o feedback gerado
                if feedback:
                    post_feedback_comment(PR_ID, feedback)
                else:
                    post_feedback_comment(PR_ID, "Não foi possível trazer uma resposta da IA.")
            else:
                print(f"Conteúdo do commit {SOURCE_COMMIT_ID} não encontrado.")
        except Exception as e:
            print(f"Erro no processamento da PR {PR_ID}: {e}")
            post_feedback_comment(PR_ID, "Não foi possível trazer uma resposta da IA devido a um erro.")
