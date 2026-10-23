I haven't run anything, and the hunk didn't come through in your message, so I haven't seen its contents. This is the plan I'd follow once I have it. I'd assume it's the staged diff in this worktree (`<worktree>`), and I'd handle the key without ever printing it.

**1. Check whether the live key is in the diff, printing only True or False**

I'd read the key from the environment rather than pass it as a command argument, so it never shows up in `ps` or in my output:
```
git diff --cached -U0 | python3 -I -c 'import os,sys; print(os.environ["TYPESAFE_API_KEY"] in sys.stdin.read())'
```
I'd run the same check on `git diff -U0` for unstaged changes. If the hunk came from a commit range instead, I'd swap in `git diff <base>..HEAD -U0`. A True result means a real secret is in the change, and that is a blocker.

**2. Show the `.env` line with the value redacted**

```
git diff --cached -U0 -- '.env' '.env.*' '*/.env' '*/.env.*' | sed -E 's/^(\+[A-Za-z_][A-Za-z0-9_]*=).+/\1<redacted>/'
```
This shows which variable names changed without showing their values.

**3. Check whether the file should be tracked at all**

```
git check-ignore -v .env
git ls-files | rg '(^|/)\.env'
```
A real `.env` that is tracked or not gitignored is a problem. A `.env.example` or `.env.sample` file is fine if it holds placeholders.

**4. Screen for other secrets by pattern, again redacted**

```
git diff --cached -U0 | rg '^\+.*(KEY|TOKEN|SECRET|PASSWORD)\w*\s*[=:]\s*\S{16,}' | sed -E 's/([=:]\s*).+/\1<redacted>/'
```

**5. Verdict**

- **Block (fail):** the key matched in step 1, a real-looking long value sits on a non-example `.env`, or `.env` is tracked or not ignored. I'd stop, tell you which file and line, and recommend unstaging the hunk and rotating the key if it was ever committed.
- **Pass:** the value is empty or a placeholder like `changeme` or `<your-key>`, or the file is a gitignored `.env` that isn't staged.

I won't commit, push, or edit anything, and I won't load a skill. The report would name the file and variable and give a pass or fail, with no values.

**Skipped or unchecked:** I haven't seen the hunk, and step 1 only catches the exact current key, so a different or older key would need the step 4 pattern scan. It also wouldn't catch an encoded or split copy, and I wouldn't run a full-history scan with gitleaks unless you ask.
