# Painel de Pagamentos da Viagem

Gerador simples de painel para WhatsApp com:

- imagem `PNG` para postar no grupo
- resumo `TXT` para colar rapidamente
- site estatico em `site/` para publicar gratis e mandar o link no WhatsApp

## Arquivos
- [`data.json`](/Users/thiagonogueira/Documents/Agentes/Agente%20controle%20de%20pagto%20viagem/data.json): dados da viagem e status de pagamentos
- [`generate_panel.py`](/Users/thiagonogueira/Documents/Agentes/Agente%20controle%20de%20pagto%20viagem/generate_panel.py): script que valida os dados e gera as saídas
- `output/`: pasta criada automaticamente com os arquivos finais
- `site/`: board web pronto para publicar em Vercel, Netlify ou GitHub Pages
- `site/config.js`: opcional para conectar uma planilha Google publicada como CSV
- `site/admin.html`: editor visual com checkboxes para gerar um `data.json` atualizado
- `site/sheet-template.csv`: modelo de colunas para a planilha

## Como atualizar
1. Edite `paid_installments` de cada pessoa em `data.json`.
2. Para uma parcela futura antecipada, adicione o mes em `prepaid_installments`, como `Novembro/2026`.
3. Quando o casal pagar junto, aumente `paid_installments` dos dois integrantes.
4. Quando so uma pessoa pagar, aumente apenas o `paid_installments` dela; o saldo do casal abate metade da parcela.
5. Rode:

```bash
python3 generate_panel.py
```

O comando tambem sincroniza `site/data.json` e gera `site/preview.png`, usada como pre-visualizacao do link no WhatsApp.

## Como atualizar por Google Sheets
1. Crie uma planilha com as colunas de `site/sheet-template.csv`.
2. Use `Arquivo > Compartilhar > Publicar na Web`.
3. Publique a aba como `CSV`.
4. Cole a URL publicada em `site/config.js`:

```js
window.PAYMENT_DATA_SOURCE = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv";
window.PAYMENT_ADMIN_URL = "https://docs.google.com/spreadsheets/d/.../edit";
```

Quando `PAYMENT_DATA_SOURCE` estiver vazio, o site usa `site/data.json`.

Nao coloque senha no GitHub Pages: qualquer senha no HTML/JS fica publica. Para edicao privada, use permissao da sua conta Google ou GitHub.

## Editor visual
Acesse `/admin.html`, marque os meses pagos e clique em `Salvar JSON`.
O navegador baixa um arquivo `data.json` atualizado. Para refletir no site publicado, substitua `site/data.json` no GitHub por esse arquivo.

## Como publicar gratis
### Recomendado: GitHub Pages
1. Suba o repositorio para o GitHub.
2. O workflow em `.github/workflows/pages.yml` publica automaticamente a pasta `site/`.
3. No GitHub, va em `Settings > Pages`.
4. Em `Build and deployment`, selecione `GitHub Actions` se ainda nao estiver selecionado.
5. Compartilhe o link final no WhatsApp.

### Alternativas tambem gratis
- Vercel: boa se voce ja usa Vercel, mas tem mais recursos do que precisamos aqui.
- Netlify: boa para deploy arrastando a pasta `site/`, mas eu manteria GitHub Pages pela simplicidade e previsibilidade.

## Sobre a previa no WhatsApp
- O WhatsApp usa `site/preview.png` como imagem de capa do link.
- O board completo abre atualizado quando a pessoa toca no link.
- O WhatsApp pode manter cache da miniatura; se a capa antiga persistir, publique uma nova versao e reenviar o link costuma resolver.

## Regras atuais
- Total da hospedagem: `R$ 6.938,68`
- 4 casais
- Vencimento no dia `07` de cada mês
- Se o dia 7 cair em fim de semana, o vencimento é antecipado
- Parcelas por casal:
  - junho a outubro: `R$ 289,11`
  - novembro: `R$ 289,12`
- Total por casal: `R$ 1.734,67`
