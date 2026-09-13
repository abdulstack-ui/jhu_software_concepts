# GitHub Setup and Submission Workflow

This assignment is submitted from the private repository `jhu_software_concepts`, with all Module 2 work under `module_2/`.

## 1. Confirm the repository

From PowerShell:

```powershell
cd C:\Users\DELL\Desktop\jhu_software_concepts
git status
git remote -v
```

Expected:
- You are inside the existing `jhu_software_concepts` Git repository.
- `origin` points to your GitHub repository.
- The repository is private on GitHub.

If `git status` says the folder is not a Git repository, stop and fix that before submission.

## 2. Work only inside `module_2`

Expected final structure:

```text
jhu_software_concepts/
└── module_2/
    ├── scrape.py
    ├── clean.py
    ├── capture.py
    ├── verify_output.py
    ├── submission_audit.py
    ├── requirements.txt
    ├── README.md
    ├── screenshot.jpg
    ├── applicant_data.json
    ├── llm_extend_applicant_data.json
    └── llm_hosting/
```

`captured_pages/` is a local working directory and is intentionally ignored by Git.

## 3. Inspect before staging

```powershell
cd C:\Users\DELL\Desktop\jhu_software_concepts
git status --short
```

Before staging, verify there are no:
- virtual environments
- browser-profile folders
- captured raw HTML pages
- secrets, tokens, passwords, cookies, or credentials
- temporary/debug output

## 4. Stage Module 2

Only after the raw and LLM outputs are complete:

```powershell
git add module_2
git status
```

Read the staged file list carefully before committing.

## 5. Commit

```powershell
git commit -m "Complete Module 2 web scraping assignment"
```

## 6. Push

Use the branch your repository already uses. Check it with:

```powershell
git branch --show-current
```

Then push, for example:

```powershell
git push origin main
```

Replace `main` if your branch has another name.

## 7. Confirm SSH submission URL

```powershell
git remote get-url origin
```

The assignment asks for the repository SSH URL. A typical SSH remote looks like:

```text
git@github.com:USERNAME/jhu_software_concepts.git
```

If the current remote is HTTPS but the assignment explicitly requires SSH, change it only after confirming the repository URL on GitHub:

```powershell
git remote set-url origin git@github.com:USERNAME/jhu_software_concepts.git
```

Then verify:

```powershell
git remote -v
```

## 8. Final repository check

After pushing:

```powershell
git status
git log -1 --oneline
```

Expected:
- working tree clean
- latest Module 2 commit visible
- all required Module 2 deliverables visible on the private GitHub repository
- repository remains private

Do not submit until `submission_audit.py` also passes the local deliverable checks.
