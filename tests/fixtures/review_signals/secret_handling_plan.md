# Token store plan

### Task 1: Keep the API token out of the config file

**Files:**
- Modify: `src/config/token_store.py`

- [ ] Read the token from the system keyring instead of the config file
- [ ] Set the credentials file permissions to 0600 when it is created

Shell rules for every executor:
- English only. Never print or write a secret, never print a process environment.
- No secrets and no machine paths in fixtures.
