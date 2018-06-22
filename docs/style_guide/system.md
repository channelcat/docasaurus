System/Internal Documentation
=============================

System docs are meant for people on our team or who would be using the product/service as a developer. this seems to be the most important part  as it allows everyone on the team to work in systems they may be unfamiliar with.
Here are the pieces of an internal documentation:

## Reference
 * Documentation of the code itself. Think java docs or in-code documentation, functions and their parameters
 * Dependencies and requirements
   * Docker
   * Setting up MySQL
   * Setting up AWS instances
   * Development requirements
## How-To Guides
 * How to get access to requirements
 * How to make a specific thing:
   * How to make an API endpoint
   * How to make a module
   * How to create a new “tool”
 * Development
   * How to set up dev environment
   * How to setup my IDE
   * How to contribute (I.E. pull request? Code validation?)
   * How to deploy the service
   * How to test
## Architecture
 * A Diagram and short explanation of each part of the service (on a very high level)
 * Link to RFC
## Operations
 * Locations of servers, IPs, AWS instances etc.
 * How to get passwords/credentials to log into machines
 * Runbook
   * Common Problems/troubleshooting (should add to everytime something is fixed/On-call incident)
   * Common Actions
     * Change a configuration value
     * Restart the service