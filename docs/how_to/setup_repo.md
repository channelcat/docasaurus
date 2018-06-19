Setting up a Repo
=================

Navigate to the main page of docasaurus.  Enter your repo information and click "Setup Docs."  For the initial setup, 
admin permissions will be required.  If you do not wish to grant admin permissions to the docasaurus user, add the hook 
manually to the git repo `https://DOCASAURUS_URL/api/v1/githook` where `DOCASAURUS_URL` is the docasaurus server.

Once set up your repo will now have a badge and github pages.  Now is a great time to click the badge and make sure the 
build went through OK.  If it didn't, you can fix the errors in your docs and re-commit, or you can check out 
[How to test locally](./testing.md).  From here you can check your coverage %, and see tips to improve your 
documentation usefulness.