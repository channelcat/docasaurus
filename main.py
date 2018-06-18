from flask import Flask, jsonify, request,  send_from_directory
from glob import glob
from tempfile import TemporaryDirectory
from subprocess import check_output, STDOUT, CalledProcessError
from os import environ, listdir, path, unlink
from io import StringIO
from shutil import move, rmtree
from github import Github, UnknownObjectException
import re

APP_URL = environ.get('APP_URL')
GIT_HOST = environ.get('GIT_HOST', 'github.com')
GIT_API_URL = 'https://api.github.com' if GIT_HOST == 'github.com' else f'https://{GIT_HOST}/api'
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

@app.route('/')
def index():
    return send_from_directory('/code', 'index.html')

@app.route('/githook', methods=['POST'])
def githook():
    post_data = request.get_json()
    owner, repo = post_data.get('repository', {}).get('full_name').split('/')
    return setup(owner, repo)

@app.route('/setup/<owner>/<repo>')
def setup(owner, repo):
    needs_create_hook = True
    needs_create_readme = True
    needs_add_badge = True

    try:
        repo = github.get_repo(f'{owner}/{repo}')
        for hook in repo.get_hooks():
            hook_url = hook.config.get('url', '')
            if APP_URL in hook_url:
                needs_create_hook = False
                break
    except UnknownObjectException:
        return jsonify({ "success": False, "error": f"Unable to access repo.  Be sure `{GIT_USERNAME}` has write access to the repo." })
    except Exception as e:
        return jsonify({ "success": False, "error": f"An error occurred: {e}" })
    
    if needs_create_hook:
        repo.create_hook(name='web', config={'url': f'{APP_URL}/githook', 'content_type': 'json'}, events=['push'])

    return jsonify({ 
        "success": True, 
        "hook": "created" if needs_create_hook else "ready",
        "readme": "created" if needs_create_readme else "ready",
        "badge": "created" if needs_add_badge else "ready",
    })

@app.route('/process/<owner>/<repo>')
def process(owner, repo):
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
        return jsonify({ 'success': True, 'ls': ls, 'branch_created': is_new_branch, 'updated': updated })
    except Exception as e:
        return jsonify({ 'success': False, 'error': str(e) })
    finally:
        repo_dir.cleanup()
        docs_dir.cleanup()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
