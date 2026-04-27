# One-time GitHub Pages setup

The wood-shop folder is a fully static site, perfect for GitHub Pages. After this five-minute setup, the **scheduled `wood-shop-refresh` task will publish updates automatically** — every Monday it scrapes both vendors, regenerates `index.html`, and pushes to your repo. GitHub Pages republishes the site within a minute.

## Why this script-based publish (vs. plain `git init`)?

The Cowork sandbox can write to your `Cowork Experiments` folder but isn't allowed to *delete* files in it (a safety guard). Git constantly creates and removes lock/index files, so an in-place `git init` won't work from inside Cowork. Instead, `scripts/publish.sh` clones the repo into ephemeral scratch space, mirrors your workspace into it (`rsync` minus the secret files), and pushes from there.

## Step 1 — Create the GitHub repo

1. Go to <https://github.com/new>
2. **Repository name:** `wood-shop` (or anything you like)
3. **Visibility:** Public (required for free GitHub Pages on personal accounts)
4. **Do NOT** check "Add a README" — leave the repo empty.
5. Click **Create repository**.
6. Note the URL (looks like `https://github.com/seandanielson/wood-shop`).

## Step 2 — Generate a Personal Access Token (fine-grained)

1. Go to <https://github.com/settings/tokens?type=beta>
2. Click **Generate new token**.
3. **Token name:** `wood-shop-publish`
4. **Expiration:** 1 year (or whatever you prefer — set a reminder to rotate)
5. **Repository access:** *Only select repositories* → pick the `wood-shop` repo you just made
6. **Permissions** → *Repository permissions* → set **Contents: Read and write** (everything else stays "No access")
7. Click **Generate token** and copy the value (you won't see it again).

## Step 3 — Drop the token + repo URL into the workspace

In the `wood-shop` folder, create two single-line files (no trailing newline):

- `.gh-token` — paste the token value
- `.repo-url` — paste the repo path *without* protocol or `.git` suffix, e.g. `github.com/seandanielson/wood-shop`

Both filenames are in `.gitignore` and excluded from the publish, so they stay local.

You can do this from the macOS Terminal:

```bash
cd ~/Documents/Cowork\ Experiments/wood-shop
printf 'github_pat_xxxxxxxx' > .gh-token              # replace with your token
printf 'github.com/YOUR_USERNAME/wood-shop' > .repo-url
chmod 600 .gh-token .repo-url
```

## Step 4 — Run the first publish

```bash
cd ~/Documents/Cowork\ Experiments/wood-shop
bash scripts/publish.sh "Initial publish"
```

You should see lines like `[publish] Cloning…`, `[publish] Mirroring…`, `[publish] Pushing…`, `[publish] Done.`

If you get `Empty / new repo — bootstrapping main branch.` followed by a successful push, that's normal for the first run.

## Step 5 — Enable GitHub Pages

1. On GitHub, open your `wood-shop` repo.
2. **Settings → Pages**.
3. **Source:** *Deploy from a branch*.
4. **Branch:** `main` / `(root)`. Save.
5. Wait ~30 seconds. The page banner will show your live URL — usually `https://YOUR_USERNAME.github.io/wood-shop/`.

That's it. The site will rebuild automatically every time the scheduled task pushes (or anytime you run `publish.sh` manually).

## Step 6 — Pre-approve the publish step in the scheduled task

The scheduled `wood-shop-refresh` task already includes a publish step. The first time it runs after this setup, it may pause asking for permission to run `bash scripts/publish.sh`. To avoid that, click **Run now** once on the task in the Cowork **Scheduled** sidebar — approvals you grant carry over to future runs.

## Troubleshooting

**"`.gh-token` or `.repo-url` not found — skipping publish."**
You haven't created the secret files yet. See Step 3.

**"remote: Permission to … denied"**
The token doesn't have *Contents: Read and write* on this repo. Regenerate with the right scope.

**"fatal: refusing to merge unrelated histories"**
Your repo isn't empty (you accidentally added a README on creation). Easiest fix: delete the repo on GitHub, recreate it empty, run `publish.sh` again.

**Publish keeps saying "no changes"**
Run `python3 scripts/regenerate.py` first so `index.html` reflects the latest `products.json`.

**Token compromised**
Revoke at <https://github.com/settings/tokens?type=beta> and generate a new one.
