from flask import Flask, jsonify, redirect, request, send_from_directory, Response
from glob import glob
from tempfile import TemporaryDirectory
from subprocess import check_output, STDOUT, CalledProcessError
from os import environ, listdir, path, unlink, rename, walk
from io import StringIO
from shutil import move, rmtree, copytree, copy
from github import Github, UnknownObjectException
from storage import set_status, get_status
import re
import requests

APP_URL = environ.get('APP_URL')
GIT_HOST = environ.get('GIT_HOST', 'github.com')
GIT_API_URL = 'https://api.github.com' if GIT_HOST == 'github.com' else f'https://{GIT_HOST}/api/v3'
GIT_USERNAME = environ.get('GIT_USERNAME')
GIT_PASSWORD = environ.get('GIT_PASSWORD')
GIT_COMMITTER_NAME = environ.get('GIT_COMMITTER_NAME')
GIT_COMMITTER_EMAIL = environ.get('GIT_COMMITTER_EMAIL')
github = Github(GIT_USERNAME, GIT_PASSWORD, base_url=GIT_API_URL)

app = Flask('docasaurus')

def run(*args, **kwargs):
    try:
        return check_output(*args, **kwargs, stderr=STDOUT)
    except CalledProcessError as e:
        raise Exception(e.output.decode())

def move_files(source, destination):
    for _file in glob(f'{source}/*'):
        move(_file, destination)
    return True

def remove_files(source, ignore=()):
    for _file in listdir(source):
        if _file in ignore:
            continue
        
        file_path = f'{source}/{_file}'
        if path.isdir(file_path):
            rmtree(file_path)
        else:
            unlink(file_path)
    return True

def replace_in_files(directory, replacements):
    for root, dirs, files in walk(directory):
        for name in files:
            file_path = path.join(root, name)
            with open(file_path) as file:
                contents = file.read()
            with open(file_path, 'w') as file:
                contents = replace_in_str(contents, replacements)
                file.write(contents)

def replace_in_str(string, replacements):
    for k, v in replacements.items():
        string = string.replace('{' + k + '}', v)
    return string

@app.route('/')
def index():
    return send_from_directory('/code', 'index.html')

@app.route('/status/<owner>/<repo>')
def status(owner, repo):
    return send_from_directory('/code', 'status.html')

@app.route('/badge/<owner>/<repo>')
def badge(owner, repo):
    status = get_status(owner, repo)
    url = "https://img.shields.io/badge/docs-unknown-lightgrey.svg"
    if status.get('status') == 'success':
        url = f"https://img.shields.io/badge/docs-{status.get('coverage', 100)}%25-brightgreen.svg"
    elif status.get('status') == 'building':
        url = "https://img.shields.io/badge/docs-building-blue.svg"
    elif status.get('status') == 'error':
        url = "https://img.shields.io/badge/docs-error-red.svg"
    
    response = requests.get(url)
    return Response(response.text, mimetype=response.headers.get('Content-Type'))

@app.route('/api/v1/githook', methods=['POST'])
def githook():
    post_data = request.get_json()
    owner, repo = post_data.get('repository', {}).get('full_name').split('/')
    if post_data.get('ref') == 'refs/heads/master':
        return process(owner, repo)
    else:
        return jsonify({'build': False})

@app.route('/api/v1/setup/<owner>/<repo>')
def setup(owner, repo):
    needs_create_hook = True
    needs_create_readme = True
    needs_create_docs = True
    needs_add_badge = True
    request_create_docs = request.args.get('createDocs') == 'true'
    request_add_badge = request.args.get('addBadge') == 'true'

    repo_name = repo
    repo_dir = TemporaryDirectory()
    repo_url = f'https://{GIT_HOST}/{owner}/{repo}.git'
    repo_uri = f'{owner}/{repo}' if GIT_HOST == 'github.com' else f'https://{GIT_HOST}/{owner}/{repo}'
    pages_url = f'https://{owner}.github.io/{repo}' if GIT_HOST == 'github.com' else f'https://{GIT_HOST}/pages/{owner}/{repo}'
    badge_image_url = f'{APP_URL}/badge/{owner}/{repo_name}'
    status_url = f'{APP_URL}/status/{owner}/{repo_name}'
    readme_path = f'{repo_dir.name}/README.md'
    docs_path = f'{repo_dir.name}/docs'
    try:
        # Check if hook is needed
        repo = github.get_repo(f'{owner}/{repo}')
        for hook in repo.get_hooks():
            hook_url = hook.config.get('url', '')
            if APP_URL in hook_url:
                needs_create_hook = False
                break
        
        # Check if README.md and docs are needed
        run(['git', 'clone', repo_url, repo_dir.name])
        needs_create_readme = not path.exists(readme_path)
        needs_create_docs = not path.exists(docs_path) and request_create_docs

        # Check if badge is needed
        if not needs_create_readme:
            needs_add_badge = badge_image_url not in open(readme_path).read()
        if not request_add_badge:
            needs_add_badge = False
    
        replacements = {
            'github_uri': repo_uri,
            'ghpages_url': pages_url,
            'project_name': repo.name,
        }

        if needs_create_hook:
            repo.create_hook(name='web', config={'url': f'{APP_URL}/api/v1/githook', 'content_type': 'json'}, events=['push'])
        if needs_create_readme:
            files_list = {f.lower(): f for f in listdir(repo_dir.name)}
            if 'readme.md' in files_list:
                rename(f"{repo_dir.name}/{files_list['readme.md']}", readme_path)
            else:
                readme_contents = open('/code/template/README.md').read()
                readme_contents = replace_in_str(readme_contents, replacements)
                open(readme_path, 'w+').write(readme_contents)
        if needs_create_docs:
            copytree('/code/template/docs', docs_path)
            run(['git', 'add', 'docs'], cwd=repo_dir.name)
            replace_in_files(docs_path, replacements)
        if needs_add_badge:
            readme = open(readme_path).read()
            badge = f'\n[![Documentation]({badge_image_url})]({status_url})\n'
            badge_position = readme.find('[')
            if badge_position == -1:
                badge_position = readme.find('\n') + 1
            if badge_position > 0:
                readme = readme[:badge_position] + badge + readme[badge_position:]
            else:
                readme = badge + readme
            open(readme_path, 'w').write(readme)

        # Push changes to Git
        if needs_create_readme or needs_add_badge or needs_create_docs:
            run(['git', 'add', 'README.md'], cwd=repo_dir.name)
            run(['git', '-c', f'user.name={GIT_COMMITTER_NAME}', '-c', f'user.email={GIT_COMMITTER_EMAIL}', 
                 'commit', '-am', 'Added README.md'], cwd=repo_dir.name)
            run(['git', 'push', 'origin', 'master'], cwd=repo_dir.name)

    except UnknownObjectException:
        return jsonify({ "success": False, "error": f"Unable to access repo.  Be sure `{GIT_USERNAME}` has admin access to the repo.  You can limit access to 'write' after setup." })
    # except Exception as e:
    #     return jsonify({ 'success': False, 'error': str(e) })
    finally:
        repo_dir.cleanup()

    return jsonify({ 
        "success": True, 
        "hook": "created" if needs_create_hook else "ready",
        "readme": "created" if needs_create_readme else "ready",
        "docs": "created" if needs_create_docs else ("ready" if request_create_docs else "skip"),
        "badge": "created" if needs_add_badge else ("ready" if request_add_badge else "skip"),
    })

@app.route('/api/v1/process/<owner>/<repo>')
def process(owner, repo):
    set_status(owner, repo, status='building')
    repo_dir = TemporaryDirectory()
    docs_dir = TemporaryDirectory()
    try:
        repo_url = f'https://{GIT_HOST}/{owner}/{repo}.git'

        # Pull Git Repo
        try:
            remote_branches = run(['git', 'ls-remote', '--heads', repo_url]).decode()
            is_new_branch = 'refs/heads/gh-pages' not in remote_branches
            run(['git', 'clone', repo_url, repo_dir.name])
        except Exception as e:
            raise Exception(f'Unable to check braches.  Be sure `{GIT_USERNAME}` has write access to the repo.')

        # Build Docs
        try:
            run(['docpress', 'build'], cwd=repo_dir.name)
        except Exception as e:
            errors = re.findall(r'Error: (.+)', str(e))
            error = errors[0] if errors else 'Unknown'
            raise Exception(f'Unable to build docs.  Error: {error}')

        # Setup docs branch
        try:
            move_files(f'{repo_dir.name}/_docpress', docs_dir.name)
            rmtree(f'{repo_dir.name}/_docpress')
            if is_new_branch:
                run(['git', 'checkout', '--orphan', 'gh-pages'], cwd=repo_dir.name)
            else:
                run(['git', 'checkout', 'gh-pages'], cwd=repo_dir.name)
            run(['git', 'rm', '--cached', '-r', '.'], cwd=repo_dir.name)
            remove_files(repo_dir.name, ignore=['.git'])
            move_files(docs_dir.name, repo_dir.name)
        except Exception as e:
            raise Exception(f'Unable to process gh-pages branch.  Error: {e}')

        # Update docs branch
        updated = True
        try:
            run(['git', 'add', '.'], cwd=repo_dir.name)
            run([
                'git', 
                    '-c', f'user.name={GIT_COMMITTER_NAME}', 
                    '-c', f'user.email={GIT_COMMITTER_EMAIL}', 
                'commit', '-am', 'Updated documentation'
                ], cwd=repo_dir.name)
            run(['git', 'push', 'origin', 'gh-pages'], cwd=repo_dir.name)
        except Exception as e:
            if 'nothing to commit' in str(e):
                updated = False
            else:
                raise Exception(f'Unable to update gh-pages branch.  Be sure `{GIT_USERNAME}` has write access to the repo.  Error: {e}')
        
        ls = run(['ls', '-a', repo_dir.name]).decode().split('\n')
        set_status(owner, repo, status='success', coverage=100)
        return jsonify({ 'success': True, 'ls': ls, 'branch_created': is_new_branch, 'updated': updated })
    except Exception as e:
        set_status(owner, repo, status='error', message=str(e))
        return jsonify({ 'success': False, 'error': str(e) })
    finally:
        repo_dir.cleanup()
        docs_dir.cleanup()

@app.route('/api/v1/status/<owner>/<repo>')
def api_status(owner, repo):
    repo_url = f'https://{GIT_HOST}/{owner}/{repo}'
    pages_url = f'https://{owner}.github.io/{repo}' if GIT_HOST == 'github.com' else f'https://{GIT_HOST}/pages/{owner}/{repo}'
    return jsonify({'repo_url': repo_url, 'pages_url': pages_url, **get_status(owner, repo)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
