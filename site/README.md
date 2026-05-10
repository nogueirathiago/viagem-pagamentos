# Board de Pagamentos da Viagem

Esta pasta contem o site estatico pronto para publicar gratis.

## Opcao recomendada: GitHub Pages

1. Suba o repositorio para o GitHub.
2. O workflow em `.github/workflows/pages.yml` publica esta pasta `site/`.
3. No GitHub, va em `Settings > Pages`.
4. Em `Build and deployment`, selecione `GitHub Actions` se ainda nao estiver selecionado.
5. O GitHub vai gerar um link publico para compartilhar no WhatsApp.

## Atualizacao por planilha

Se quiser atualizar pelo celular, publique uma planilha Google como CSV e cole a URL em `config.js`.

```js
window.PAYMENT_DATA_SOURCE = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv";
```

Se `PAYMENT_DATA_SOURCE` ficar vazio, o site usa `data.json`.
