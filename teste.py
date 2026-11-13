"""Teste do gerar.py com uma CentralCart de mentira (sem chave de verdade, sem internet).

    python teste.py
"""
import datetime
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import urllib.parse

import gerar

AGORA = datetime.datetime.now(gerar.FUSO)
INICIO, FIM = gerar.mes_de(AGORA)


def pedido(nick, valor, quando, status='APPROVED'):
    return {'internal_id': 'p%d' % id(quando), 'client_identifier': nick, 'price': valor, 'status': status,
            'paid_at': quando.astimezone(datetime.timezone.utc).isoformat().replace('+00:00', 'Z'), 'created_at': quando.isoformat()}


MEIO = INICIO + datetime.timedelta(days=5, hours=3)
PEDIDOS = (
    [pedido('LIONS', 300, MEIO), pedido('lions', 200, MEIO), pedido('Filipinho', 400, MEIO), pedido('am4ymon', 250, MEIO)]
    + [pedido('Jogador%02d' % i, 10 + i, MEIO) for i in range(1, 12)]
    + [pedido('MesPassado', 9999, INICIO - datetime.timedelta(hours=2)),      # pago antes do mês: fora
       pedido('Estornado', 9999, MEIO, 'CHARGEDBACK'),                         # não aprovado: fora
       pedido('', 50, MEIO), pedido('Zerado', 0, MEIO)]
)
CHAMADAS = []


class Falsa(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query, keep_blank_values=True)
        CHAMADAS.append((self.headers.get('Authorization'), q))
        ini = int(q['page_cursor'][0] or 0)
        tam = 7  # páginas pequenas, para exercitar o cursor
        fatia = PEDIDOS[ini:ini + tam]
        corpo = json.dumps({'data': fatia, 'next_cursor': str(ini + tam) if ini + tam < len(PEDIDOS) else None}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *a):
        pass


def main():
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Falsa)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    pasta = tempfile.mkdtemp()
    saida = os.path.join(pasta, 'top.json')
    env = dict(os.environ, CENTRALCART_API='http://127.0.0.1:%d' % srv.server_port, CENTRALCART_API_KEY='chave-de-teste', PYTHONIOENCODING='utf-8')
    aqui = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(aqui, 'config.json'), encoding='utf-8') as f:
        assert 'excluir' in json.load(f)
    r = subprocess.run([sys.executable, os.path.join(aqui, 'gerar.py'), saida], env=env, capture_output=True, text=True, encoding='utf-8')
    print(r.stdout.strip(), r.stderr.strip())
    assert r.returncode == 0, r
    d = json.load(open(saida, encoding='utf-8'))
    top = d['top']
    print(json.dumps(d, ensure_ascii=False))
    # 1) soma por nick sem diferenciar maiúscula; 2) ordem; 3) dez no máximo
    assert [t['nick'] for t in top[:3]] == ['LIONS', 'Filipinho', 'am4ymon'], top[:3]
    assert len(top) == 10 and [t['pos'] for t in top] == list(range(1, 11))
    # porcentagem = caminho até a posição de cima: 400/500 = 80, 250/400 = 62, líder = 100
    assert [t['pct'] for t in top[:3]] == [100, 80, 62], top[:3]
    assert all(1 <= t['pct'] <= 99 for t in top[1:])
    # quem não entra: mês passado, estornado, sem nick, valor zero
    nicks = {t['nick'] for t in top}
    assert not nicks & {'MesPassado', 'Estornado', 'Zerado', ''}, nicks
    # nenhum valor em dinheiro no arquivo: só as chaves esperadas e nenhum número além de posição e porcentagem
    assert set(d) == {'mes', 'mes_nome', 'resultado_em', 'mudou_em', 'top'} and all(set(t) == {'pos', 'nick', 'pct'} for t in top)
    texto = open(saida, encoding='utf-8').read()
    assert '9999' not in texto and '500' not in texto and 'price' not in texto
    assert d['mes'] == INICIO.strftime('%Y-%m') and d['resultado_em'] == FIM.isoformat()
    # a chave vai no cabeçalho e o filtro pede só aprovados; paginou até o fim
    assert all(a == 'Bearer chave-de-teste' and q['status'] == ['APPROVED'] for a, q in CHAMADAS) and len(CHAMADAS) == 3, len(CHAMADAS)
    # rodar de novo sem mudança não regrava (o agendamento só publica quando o ranking muda)
    antes = os.path.getmtime(saida)
    r = subprocess.run([sys.executable, os.path.join(aqui, 'gerar.py'), saida], env=env, capture_output=True, text=True, encoding='utf-8')
    assert 'sem mudança' in r.stdout and os.path.getmtime(saida) == antes, r.stdout
    # lista de exclusão (config.json): a conta de teste da equipe sai do ranking
    com_staff = PEDIDOS + [pedido('StaffTeste', 9999, MEIO)]
    rank = gerar.ranking(com_staff, INICIO, FIM, excluir=['stafftESTE'])
    assert 'StaffTeste' not in [n for n, _ in rank] and rank[0][0] == 'LIONS'
    assert gerar.ranking(com_staff, INICIO, FIM)[0][0] == 'StaffTeste'
    # sem chave: avisa e sai sem erro
    env2 = dict(env)
    env2.pop('CENTRALCART_API_KEY')
    r = subprocess.run([sys.executable, os.path.join(aqui, 'gerar.py'), os.path.join(pasta, 'x.json')], env=env2, capture_output=True, text=True, encoding='utf-8')
    assert r.returncode == 0 and 'sem CENTRALCART_API_KEY' in r.stdout and not os.path.exists(os.path.join(pasta, 'x.json'))
    print('OK')


if __name__ == '__main__':
    main()
