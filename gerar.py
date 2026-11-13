"""Calcula o top 10 doadores do mês da loja da Pokémania e grava top.json.

O arquivo publicado tem só nicks e porcentagens. Nenhum valor em dinheiro sai daqui: a soma de cada jogador fica na
memória deste script e vira "quantos por cento do caminho até a posição de cima".

    CENTRALCART_API_KEY=cc_sk_... python gerar.py [saida.json]

A chave precisa só da permissão de leitura de pedidos. Sem a chave o script avisa e sai sem erro (não publica nada).
"""
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import zoneinfo

API = os.environ.get('CENTRALCART_API', 'https://api.centralcart.io/v1')
FUSO = zoneinfo.ZoneInfo('America/Sao_Paulo')
AQUI = os.path.dirname(os.path.abspath(__file__))
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
QUANTOS = 10
MAX_PAGINAS = 500  # 100 mil pedidos no mês: trava de segurança contra laço infinito


def config():
    try:
        with open(os.path.join(AQUI, 'config.json'), encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def data_de(texto):
    """Data da API -> datetime com fuso. Sem fuso no texto, vale UTC."""
    if not texto:
        return None
    try:
        d = datetime.datetime.fromisoformat(str(texto).replace('Z', '+00:00'))
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=datetime.timezone.utc)


def pedidos(chave, de, ate):
    """Pedidos aprovados criados entre as duas datas (AAAA-MM-DD), página por página."""
    cursor = ''
    for _ in range(MAX_PAGINAS):
        q = urllib.parse.urlencode({'page_cursor': cursor, 'page_size': 200, 'from': de, 'to': ate, 'status': 'APPROVED'})
        req = urllib.request.Request('%s/app/order?%s' % (API, q), headers={'Authorization': 'Bearer ' + chave, 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.load(r)
        itens = d.get('data') or []
        yield from itens
        cursor = d.get('next_cursor') or (d.get('meta') or {}).get('next_cursor') or ''
        if not cursor or not itens:
            return
    raise SystemExit('pedidos demais: passou de %d páginas' % MAX_PAGINAS)


def ranking(lista, inicio, fim, excluir=()):
    """lista de pedidos -> [(nick, total)] do maior para o menor, só do que foi pago dentro do mês."""
    excluir = {n.strip().lower() for n in excluir}
    total, nome = {}, {}
    for p in lista:
        if (p.get('status') or 'APPROVED') != 'APPROVED':
            continue
        nick = str(p.get('client_identifier') or '').strip()
        if not nick or nick.lower() in excluir:
            continue
        quando = data_de(p.get('paid_at')) or data_de(p.get('created_at'))
        if quando is not None and not (inicio <= quando < fim):
            continue
        try:
            valor = float(p.get('price') or 0)
        except (TypeError, ValueError):
            continue
        if valor <= 0:
            continue
        chave = nick.lower()
        total[chave] = total.get(chave, 0.0) + valor
        nome.setdefault(chave, nick)  # a lista vem do mais recente: fica a grafia do último pedido
    return sorted(((nome[k], v) for k, v in total.items()), key=lambda x: (-x[1], x[0].lower()))


def publico(rank, agora, inicio, fim):
    """O que vai para o site: posição, nick e a porcentagem do caminho até a posição de cima (o líder fica com 100)."""
    top = []
    for i, (nick, valor) in enumerate(rank[:QUANTOS]):
        if i == 0:
            pct = 100
        else:
            pct = min(99, int(100 * valor / rank[i - 1][1]))  # nunca 100: quem empatou ainda não passou
        top.append({'pos': i + 1, 'nick': nick, 'pct': pct})
    return {
        'mes': inicio.strftime('%Y-%m'),
        'mes_nome': MESES[inicio.month - 1],
        'resultado_em': fim.isoformat(),  # os top doadores são declarados na virada do mês, à meia-noite
        'mudou_em': agora.isoformat(timespec='seconds'),
        'top': top,
    }


def mes_de(agora):
    inicio = agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    fim = (inicio + datetime.timedelta(days=32)).replace(day=1)
    return inicio, fim


def main():
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, 'top.json')
    chave = os.environ.get('CENTRALCART_API_KEY', '').strip()
    if not chave:
        print('sem CENTRALCART_API_KEY: nada foi gerado')
        return 0
    agora = datetime.datetime.now(FUSO)
    inicio, fim = mes_de(agora)
    # a API filtra pela criação do pedido; o que vale aqui é o pagamento. Uns dias de folga antes cobrem o pedido
    # criado no fim do mês passado e pago neste.
    de = (inicio - datetime.timedelta(days=4)).strftime('%Y-%m-%d')
    ate = (agora + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    try:
        lista = list(pedidos(chave, de, ate))
    except urllib.error.HTTPError as e:
        print('a CentralCart respondeu %s: %s' % (e.code, e.read()[:200].decode('utf-8', 'replace')))
        return 1
    rank = ranking(lista, inicio, fim, config().get('excluir', []))
    novo = publico(rank, agora, inicio, fim)
    try:
        with open(saida, encoding='utf-8') as f:
            velho = json.load(f)
    except (FileNotFoundError, ValueError):
        velho = {}
    if velho.get('top') == novo['top'] and velho.get('mes') == novo['mes']:
        print('sem mudança: %d no ranking' % len(novo['top']))
        return 0
    with open(saida, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(novo, f, ensure_ascii=False, indent=1)
        f.write('\n')
    print('gravado: %d no ranking de %s' % (len(novo['top']), novo['mes']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
