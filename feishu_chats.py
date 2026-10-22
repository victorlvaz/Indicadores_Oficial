"""Lista os grupos do Feishu em que o app (bot) está e mostra o chat_id de cada um.
Rodar na pasta do projeto:   python feishu_chats.py
Pede o App ID e o App Secret (o secret não aparece enquanto você digita e não é gravado em lugar nenhum)."""
import getpass

import requests

dominio = (input("Domínio [Enter = https://open.feishu.cn; Lark internacional = https://open.larksuite.com]: ").strip()
           or "https://open.feishu.cn").rstrip("/")
app_id = input("App ID (cli_...): ").strip()
app_secret = getpass.getpass("App Secret: ").strip()

r = requests.post(f"{dominio}/open-apis/auth/v3/tenant_access_token/internal",
                  json={"app_id": app_id, "app_secret": app_secret}, timeout=30)
d = r.json()
if d.get("code") != 0:
    raise SystemExit(f"Não autenticou: {d.get('msg')} (código {d.get('code')}). Confira App ID, App Secret e o domínio.")
cab = {"Authorization": "Bearer " + d["tenant_access_token"]}

r = requests.get(f"{dominio}/open-apis/im/v1/chats", headers=cab, params={"page_size": 100}, timeout=30)
d = r.json()
if d.get("code") != 0:
    raise SystemExit(f"Não listou os grupos: {d.get('msg')} (código {d.get('code')}).")
grupos = d["data"].get("items", [])
if not grupos:
    raise SystemExit("O app não está em nenhum grupo. Adicione-o ao grupo (Configurações → Bots) e rode de novo.")
print("\nGrupos em que o app está:")
for g in grupos:
    print(f"  {g.get('name', '(sem nome)')}  ->  chat_id = {g['chat_id']}")
