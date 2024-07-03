import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Repository Azure Devops
REPOSITORIO_ESPECIFICO = 'Projeto_code_review'

# Substitua com seu token de acesso pessoal (PAT)
PERSONAL_ACCESS_TOKEN = 'h65ilsix3zkb5tzab34dxehf6c2vrappd346pxzqiqay2kdmotva'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if 'eventType' in data and data['eventType'] == 'git.pullrequest.created':
        # Verificar se o pull request é do repositório específico
        repo_name = data['resource']['repository']['name']
        if repo_name == REPOSITORIO_ESPECIFICO:
            print('Novo pull request criado no repositório específico:')
            print('Título:', data['resource']['title'])
            print('Descrição:', data['resource']['description'])
            print('Autor:', data['resource']['createdBy']['displayName'])
            
            # Obter detalhes do pull request
            pull_request_url = data['resource']['url']
            changes_url = f"{pull_request_url}/changes"
            
            response = requests.get(changes_url, auth=('', PERSONAL_ACCESS_TOKEN))
            if response.status_code == 200:
                changes = response.json()
                print('Alterações de código:')
                for change in changes['value']:
                    print('Arquivo:', change['item']['path'])
                    print('Tipo de alteração:', change['changeType'])
                    print()
            else:
                print('Erro ao obter as alterações de código:', response.status_code)
        else:
            print(f'Pull request ignorado. Repositório: {repo_name}')
    
    return jsonify({'status': 'received'}), 200

if __name__ == '__main__':
    app.run(port=5000, debug=True)
