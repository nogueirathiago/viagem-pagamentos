# Handoff - Painel de Pagamentos da Viagem

## Current State
- Public board: `https://nogueirathiago.github.io/viagem-pagamentos/`
- Admin board: `https://nogueirathiago.github.io/viagem-pagamentos/admin.html`
- GitHub repo: `https://github.com/nogueirathiago/viagem-pagamentos`
- Deployment: GitHub Pages via `.github/workflows/pages.yml`, publishing the `site/` folder.
- Current visible label: `Viagem réveillon 2027`.
- Public dashboard design: neutral background, metric cards, progress colors from red at 0% to green at 100%.
- WhatsApp preview: `site/preview.png`, referenced by `og:image` with a version query string.

## Main Files
- `site/index.html`: public dashboard structure and Open Graph metadata.
- `site/styles.css`: public dashboard and admin styling.
- `site/app.js`: public dashboard calculations and rendering.
- `site/admin.html`: checkbox-based payment editor.
- `site/admin.js`: saves checked payments to GitHub using a user-provided fine-grained token.
- `site/data.json`: data used by the published site.
- `data/payments.json`: local source used by the Python generator.
- `scripts/generate_panel.py`: generates `artifacts/whatsapp/painel_pagamentos_whatsapp.png`, text summary, `site/preview.png`, and syncs `site/data.json` from `data/payments.json`.

## Payment Rules
- Total hospedagem: `R$ 6.938,68`.
- 4 casais, 8 pessoas, 6 parcelas.
- Total por casal: `R$ 1.734,67`.
- Vencimentos: dia 07 de cada mês, antecipando se cair em fim de semana.
- Parcelas por casal: junho a outubro `R$ 289,11`; novembro `R$ 289,12`.
- `paid_installments`: parcelas sequenciais a partir de junho.
- `prepaid_installments`: parcelas fora da ordem, por exemplo `Novembro/2026`.
- Saldo por casal abate metade quando só uma pessoa paga e abate a parcela cheia quando os dois pagam.

## Admin Behavior
- Admin page is publicly viewable, but only saves with a valid GitHub fine-grained token.
- Token must have `Contents: Read and write` for repo `nogueirathiago/viagem-pagamentos`.
- Token is not committed; if user chooses remember, it is stored only in browser `localStorage`.
- Admin updates `site/data.json` through GitHub API and GitHub Pages redeploys automatically.
- `admin.js` retries once on GitHub SHA conflicts and gives friendly messages for token/permission/conflict errors.

## Validation Checklist
- Run `node --check site/app.js && node --check site/admin.js`.
- Run `python3 -m py_compile scripts/generate_panel.py`.
- If preview changes, run `python3 scripts/generate_panel.py` and inspect `site/preview.png`.
- After pushing, watch latest deploy: `gh run list --repo nogueirathiago/viagem-pagamentos --limit 1`.
- Confirm published metadata: `curl -L -s https://nogueirathiago.github.io/viagem-pagamentos/ | rg 'og:image|Viagem réveillon 2027'`.

## Git Notes
- Local repo uses personal Git config: `Thiago Nogueira <thenrique.nogueira@gmail.com>`.
- `gh` is authenticated as `nogueirathiago`.
- The remote often changes from admin saves. If push is rejected, fetch and rebase instead of overwriting:

```bash
git fetch origin
git rebase origin/main
git push
```

## Important Caveats
- GitHub Pages cannot securely protect `/admin.html`; security comes from the GitHub token required to save.
- WhatsApp caches previews aggressively. When changing `site/preview.png`, bump the `og:image` query string in `site/index.html`.
- Do not commit tokens, passwords, or screenshots containing secrets.
