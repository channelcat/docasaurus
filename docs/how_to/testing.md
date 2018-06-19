Testing
=======

When building docs for a repo, it can be taxing to test layouts or discover errors on committing.  To test docs locally
against a repo:
 * Copy `docker-compose.testing.yml` to the target repo as `docker-compose.yml`
 * Run `docker-compose up`
 * Check out `http://localhost:3000/`