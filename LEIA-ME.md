# Liga Reset 2026 no GitHub Pages (atualização automática)

Esta pasta é o repositório completo:

| Arquivo | Para que serve |
|---|---|
| `index.html` | O site (classificações, chaveamento, premiação etc.). Os dados ficam dentro dele. |
| `scripts/atualizar_rodada.py` | Busca na API do Cartola a pontuação das rodadas encerradas e grava no `index.html`. |
| `.github/workflows/atualizar-rodada.yml` | Agenda o script para rodar todo dia e publica o site. |

## Como funciona

- Roda **todo dia, 4 vezes** (07h, 13h, 19h e 23h de Brasília).
- Só busca **rodadas encerradas**. A rodada em andamento nunca é lida, porque nesse período a API devolve a pontuação da rodada anterior.
- **Não regrava** rodada que já está salva. Se ficar alguns dias sem rodar, busca todas as encerradas que faltarem.
- Se os dados vierem incompletos, zerados ou iguais aos da rodada anterior, **não salva nada** e o GitHub te manda um e-mail avisando da falha.
- Quando salva uma rodada, faz um commit no repositório e publica o site.

## Passo a passo (uma vez só)

1. Crie uma conta em https://github.com (se ainda não tiver).
2. Crie um repositório **público** (ex.: `liga-reset`) em **New repository**. Não marque nenhuma opção de README.
3. Envie os arquivos desta pasta:
   - Clique em **uploading an existing file** e arraste `index.html`, `LEIA-ME.md` e a pasta `scripts`. Depois clique em **Commit changes**.
   - A pasta `.github` costuma não subir pelo arrastar (ela é oculta no Windows). Crie o arquivo por **Add file → Create new file**: no nome digite `.github/workflows/atualizar-rodada.yml`, cole o conteúdo do arquivo desta pasta e clique em **Commit changes**.
   - Outra opção: usar o GitHub Desktop, que envia a pasta inteira de uma vez.
4. Vá em **Settings → Pages** e, em **Source**, escolha **GitHub Actions**.
5. Vá na aba **Actions**, abra **Atualizar rodada do Cartola** e clique em **Run workflow** (deixe os campos vazios). Isso faz o primeiro teste e publica o site.
6. O endereço aparece em **Settings → Pages**, no formato `https://SEU-USUARIO.github.io/liga-reset/`.

> Se o passo 5 falhar com erro de permissão no `git push`, vá em **Settings → Actions → General → Workflow permissions**, marque **Read and write permissions** e rode de novo.

## No dia a dia

Você não precisa fazer nada. Para acompanhar, abra a aba **Actions**: cada execução mostra um resumo (rodada salva, destaques, avisos).

**Corrigir ou rebuscar uma rodada:** em **Actions → Atualizar rodada do Cartola → Run workflow**, informe a rodada e marque **forcar**.

**Lançar ou corrigir na mão:** abra o site, vá em **Atualizar dados**, lance a rodada, clique em **Baixar HTML atualizado**, renomeie para `index.html` e envie no repositório no lugar do antigo (**Add file → Upload files**). O site é republicado sozinho.

**Sorteios de desempate:** são definidos na aba **Atualizar dados**, que também gera o HTML para você enviar.

**Manter o Excel em dia:** no site, em **Atualizar dados**, escolha a rodada e clique em **Copiar rodada N para o Excel**. Depois cole a partir da coluna B da aba Pontuação.

## Observações

- O repositório é público: qualquer pessoa com o link vê os nomes dos times e dos donos.
- A API do Cartola não é oficial. Se o Globo mudar ou bloquear a API, o workflow falha, você recebe o e-mail e pode voltar a lançar as rodadas pela aba **Atualizar dados**.
- O GitHub desativa agendamentos de repositórios públicos sem atividade por 60 dias. Durante a temporada isso não acontece, porque cada rodada salva gera um commit. Na próxima temporada, reative em **Actions** se precisar.
- Para mudar os horários, edite as linhas `cron` do arquivo `.github/workflows/atualizar-rodada.yml` (horário em UTC, ou seja, Brasília + 3h).
