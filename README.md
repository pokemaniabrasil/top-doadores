# Top doadores do mês (Pokémania)

Calcula o top 10 doadores do mês da loja da Pokémania e publica um arquivo pequeno, que a página
[Top doadores](https://www.pokemania.com.br/post/top-doadores) da loja lê para montar o ranking.

O arquivo publicado tem **só nicks e porcentagens**. Nenhum valor em dinheiro sai daqui.

- Publicado em: <https://pokemaniabrasil.github.io/top-doadores/top.json>
- Atualiza a cada 10 minutos (GitHub Actions). O GitHub Pages guarda o arquivo em cache por uns 10 minutos, então uma
  compra pode levar até uns 20 minutos para aparecer.

## Como funciona

1. `gerar.py` lê na API da CentralCart os pedidos **aprovados** do mês (fuso de Brasília), soma por nick e ordena.
2. Para cada posição grava a porcentagem do caminho até a posição de cima. Exemplo: o 2º com 80 já tem 80% do que o
   1º doou. O líder fica com 100.
3. O agendamento (`.github/workflows/atualizar.yml`) roda o script e, se o ranking mudou, grava o `top.json` na
   branch `gh-pages`.

Vale a data do pagamento. Pedido estornado, contestado ou cancelado deixa de contar na próxima rodada. Na virada do mês
o ranking zera.

```json
{
  "mes": "2026-11",
  "mes_nome": "novembro",
  "resultado_em": "2026-12-01T00:00:00-03:00",
  "mudou_em": "2026-11-13T16:52:33-03:00",
  "top": [
    {"pos": 1, "nick": "Jogador", "pct": 100},
    {"pos": 2, "nick": "Outro", "pct": 80}
  ]
}
```

## A chave da CentralCart

O agendamento precisa de uma chave de API da loja **só com a permissão de leitura de pedidos**:

1. No painel da CentralCart: Configurações > Integrações > gerar chave, marcando só a leitura de pedidos.
2. Neste repositório: Settings > Secrets and variables > Actions > New repository secret, com o nome
   `CENTRALCART_API_KEY`.

A chave nunca entra no código. Sem ela o script avisa e não publica nada.

## Tirar uma conta do ranking

Contas de teste ou da equipe: ponha o nick em `config.json`.

```json
{ "excluir": ["NickDeTeste"] }
```

## Testar

```bash
python teste.py
```

O teste sobe uma CentralCart de mentira na própria máquina: não usa chave nem internet.
