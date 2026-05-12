# Internal AEO Retrieval Readiness Audit MVP

Simple Streamlit demo for a local, file-based AEO retrieval-readiness audit tool.

This is an internal demo, not a SaaS product. It has no login, billing, database, or paid API integration.

## Entrypoint

Streamlit app entry file:

```text
app.py
```

## Run Locally

Install requirements:

```bash
pip install -r requirements.txt
```

Run the UI:

```bash
streamlit run app.py
```

If `streamlit` is not on your PATH, run:

```bash
python3 -m streamlit run app.py
```

The app includes a repo-relative sample page path for offline testing:

```text
inputs/sample_company_incorporation_page.html
```

## Push To GitHub

From the project root:

```bash
git init
git add .
git commit -m "Prepare Streamlit AEO audit demo"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

Before pushing, check that generated files in `outputs/` are not committed. The `.gitignore` excludes `outputs/`.

## Deploy On Streamlit Community Cloud

1. Push this project to a GitHub repository.
2. Go to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Click **New app**.
4. Select the GitHub repository and branch.
5. Set the main file path to:

```text
app.py
```

6. Deploy the app.

Streamlit Community Cloud will install dependencies from `requirements.txt`.

## Confidentiality Reminder

Do not upload confidential client data into a public demo. Use fictional or approved sample inputs unless the repository and app visibility are private and appropriate for the client data.

## Outputs

When an audit runs, the app creates the `outputs/` folder automatically and writes:

- `outputs/audit_report.md`
- `outputs/audit_scores.csv`
- `outputs/page_findings.json`
- `outputs/llm_review_prompt.md`

These generated files are ignored by Git.
