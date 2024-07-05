import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Estrutura para armazenar informações de pull requests
pull_requests = []

# Repository Azure Devops
REPOSITORIO_ESPECIFICO = 'Projeto_code_review'

# Substitua com seu token de acesso pessoal (PAT)
PERSONAL_ACCESS_TOKEN = 'h65ilsix3zkb5tzab34dxehf6c2vrappd346pxzqiqay2kdmotva'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    app.logger.info(f"Recebido webhook: {data}")
    
    if 'eventType' in data and data['eventType'] == 'git.pullrequest.created':
        # Verificar se o pull request é do repositório específico
        repo_name = data['resource']['repository']['name']
        if repo_name == REPOSITORIO_ESPECIFICO:
            app.logger.info(f"Pull request do repositório: {repo_name}")

            # Obter informações do pull request
            titulo = data['resource']['title']
            descricao = data['resource']['description']
            autor = data['resource']['createdBy']['displayName']
            
            # Obter detalhes do pull request
            pull_request_url = data['resource']['url']
            changes_url = f"{pull_request_url}/changes"
            app.logger.info(f"URL das mudanças do pull request: {changes_url}")

            # Configurar cabeçalhos de autenticação
            headers = {
                'Authorization': f'Bearer {PERSONAL_ACCESS_TOKEN}'
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
                
                # Iterar sobre as alterações de código
                for change in changes['value']:
                    file_path = change['item']['path']
                    change_type = change['changeType']
                    lines_added = change.get('linesAdded', 0)
                    lines_deleted = change.get('linesDeleted', 0)
                    
                    # Adicionar informações da alteração à lista de alterações do pull request
                    pull_request_info['alteracoes'].append({
                        'arquivo': file_path,
                        'tipo': change_type,
                        'linhas_adicionadas': lines_added,
                        'linhas_deletadas': lines_deleted
                    })
                
                # Adicionar informações do pull request à lista
                pull_requests.append(pull_request_info)
                app.logger.info(f"Pull request adicionado: {pull_request_info}")
            else:
                app.logger.error(f"Erro ao obter as alterações de código: {response.status_code}")
        else:
            app.logger.info(f"Pull request ignorado. Repositório: {repo_name}")
    
    return jsonify({'status': 'received'}), 200

@app.route('/get_pull_requests', methods=['GET'])
def get_pull_requests():
    return jsonify(pull_requests)

if __name__ == '__main__':
    app.run(port=8000, debug=True)
