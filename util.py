

from glob import glob
from shutil import move, rmtree
from os import listdir, path, walk, unlink
from subprocess import check_output, STDOUT, CalledProcessError

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