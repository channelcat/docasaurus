from os import environ
from redis import StrictRedis
import json

redis = StrictRedis(
    host=environ.get('REDIS_HOST'), 
    port=int(environ.get('REDIS_PORT')), 
    password=environ.get('REDIS_PASSWORD', ''),
    db=0,
)

def get_status_key(owner, repo):
    return f'status-{owner}-{repo}'
def get_badge_key(owner, repo):
    return f'badge-{owner}-{repo}'

def get_status(owner, repo):
    stored_value = redis.get(get_status_key(owner, repo))
    if stored_value:
        return json.loads(stored_value)
    else:
        return {'status': 'unknown'}

def set_status(owner, repo, status, message='', coverage={}):
    redis.delete(get_badge_key(owner, repo))
    return redis.set(get_status_key(owner, repo), json.dumps({
        'status': status,
        'message': message,
        'coverage': coverage,
    }))

def get_badge(owner, repo):
    return redis.get(get_badge_key(owner, repo))

def set_badge(owner, repo, badge_bytes):
    return redis.set(get_badge_key(owner, repo), badge_bytes)