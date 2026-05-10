# Board de Pagamentos da Viagem

Esta pasta contem o site estatico pronto para publicar gratis.

## Opcao recomendada: GitHub Pages

1. Crie um repositorio no GitHub.
2. Envie os arquivos desta pasta `site/` para o repositorio.
3. No GitHub, va em `Settings > Pages`.
4. Em `Build and deployment`, escolha `Deploy from a branch`.
5. Escolha o branch principal e a pasta raiz do repositorio.
6. O GitHub vai gerar um link publico para compartilhar no WhatsApp.

## Atualizacao por planilha

Se quiser atualizar pelo celular, publique uma planilha Google como CSV e cole a URL em `config.js`.

```js
window.PAYMENT_DATA_SOURCE = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv";
```

Se `PAYMENT_DATA_SOURCE` ficar vazio, o site usa `data.json`.
