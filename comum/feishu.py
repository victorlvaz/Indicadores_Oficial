"""Envio de mensagens para um grupo do Feishu/Lark por um app (bot) da empresa.

Por que um app e não o "bot personalizado" (webhook): o webhook só aceita texto. Para postar as tabelas como
IMAGEM é preciso subir a imagem pela API do app (permissão im:resource) e enviar a mensagem com a image_key.

Segredos (Streamlit: Settings > Secrets; local: .streamlit/secrets.toml):
    [feishu]
    app_id     = "cli_xxxxxxxx"
    app_secret = "xxxxxxxx"
    chat_id    = "oc_xxxxxxxx"                      # grupo OFICIAL (o bot precisa estar no grupo)
    chat_id_teste = "oc_yyyyyyyy"                   # opcional: grupo de TESTE; se existir, a tela pede para escolher o destino
    dominio    = "https://open.feishu.cn"           # Lark internacional: "https://open.larksuite.com"
    senha      = "opcional"                         # se existir, o envio pede essa senha
"""
import json

import requests

DOMINIO_PADRAO = "https://open.feishu.cn"
TIMEOUT = 90
LINHA_EM_BRANCO = [{"tag": "text", "text": "\u200b"}]      # parágrafo vazio (espaço de largura zero: o Feishu recusa texto vazio e apara espaços comuns)


def configuracao(secrets) -> dict | None:
    """Lê o bloco [feishu] dos segredos; None se faltar app_id, app_secret ou chat_id."""
    try:
        bloco = dict(secrets["feishu"])
    except Exception:                                   # sem secrets.toml / sem o bloco
        return None
    if not all(str(bloco.get(k, "")).strip() for k in ("app_id", "app_secret")):
        return None
    if not (str(bloco.get("chat_id", "")).strip() or str(bloco.get("chat_id_teste", "")).strip()):
        return None
    bloco["dominio"] = str(bloco.get("dominio") or DOMINIO_PADRAO).rstrip("/")
    return bloco


def destinos(cfg: dict) -> list[str]:
    """Destinos disponíveis: "teste" (primeiro, é o padrão) e "oficial"."""
    return [d for d, k in (("teste", "chat_id_teste"), ("oficial", "chat_id")) if str(cfg.get(k, "")).strip()]


def com_destino(cfg: dict, destino: str) -> dict:
    """Cópia da configuração apontando para o grupo escolhido ("teste" | "oficial")."""
    return {**cfg, "chat_id": cfg["chat_id_teste"] if destino == "teste" else cfg["chat_id"]}


def _resposta(r: requests.Response, o_que: str) -> dict:
    try:
        dados = r.json()
    except ValueError:
        raise RuntimeError(f"Feishu ({o_que}): resposta inválida (HTTP {r.status_code}).")
    if r.status_code != 200 or dados.get("code", 0) != 0:
        raise RuntimeError(f"Feishu ({o_que}): {dados.get('msg') or r.text[:200]} (código {dados.get('code', r.status_code)})")
    return dados


def token(cfg: dict) -> str:
    r = requests.post(f"{cfg['dominio']}/open-apis/auth/v3/tenant_access_token/internal",
                      json={"app_id": cfg["app_id"], "app_secret": cfg["app_secret"]}, timeout=TIMEOUT)
    return _resposta(r, "autenticação")["tenant_access_token"]


def subir_imagem(cfg: dict, tk: str, png: bytes, nome: str = "tabela.png") -> str:
    for tentativa in range(3):                          # subir imagem é seguro repetir (não posta nada no grupo)
        try:
            r = requests.post(f"{cfg['dominio']}/open-apis/im/v1/images", headers={"Authorization": f"Bearer {tk}"},
                              data={"image_type": "message"}, files={"image": (nome, png, "image/png")}, timeout=TIMEOUT)
            return _resposta(r, "envio da imagem")["data"]["image_key"]
        except (requests.Timeout, requests.ConnectionError):
            if tentativa == 2:
                raise
            import time
            time.sleep(2 * (tentativa + 1))


def subir_arquivo(cfg: dict, tk: str, nome: str, dados: bytes) -> str:
    """Sobe um arquivo qualquer (ex.: o Excel exportado) e devolve o file_key.
    Arquivos grandes às vezes dão erro 5xx/tempo esgotado no Feishu: tenta até 3 vezes antes de desistir."""
    import time
    mb = len(dados) / 1_048_576
    ultimo = None
    for tentativa in range(3):
        try:
            r = requests.post(f"{cfg['dominio']}/open-apis/im/v1/files", headers={"Authorization": f"Bearer {tk}"},
                              data={"file_type": "stream", "file_name": nome}, files={"file": (nome, dados)}, timeout=300)
            if r.status_code < 500:
                return _resposta(r, "envio do arquivo")["data"]["file_key"]
            ultimo = f"HTTP {r.status_code}"
        except (requests.Timeout, requests.ConnectionError) as erro:
            ultimo = type(erro).__name__
        if tentativa < 2:
            time.sleep(3 * (tentativa + 1))
    raise RuntimeError(f"Feishu (envio do arquivo): o servidor não aceitou o arquivo de {mb:.1f} MB após 3 tentativas ({ultimo}). "
                       "Tente de novo em instantes; se persistir, envie o Excel sem a base (ou menos dias).")


def enviar_arquivo(cfg: dict, tk: str, file_key: str) -> str:
    corpo = {"receive_id": cfg["chat_id"], "msg_type": "file", "content": json.dumps({"file_key": file_key})}
    r = requests.post(f"{cfg['dominio']}/open-apis/im/v1/messages?receive_id_type=chat_id",
                      headers={"Authorization": f"Bearer {tk}"}, json=corpo, timeout=TIMEOUT)
    return _resposta(r, "envio da mensagem com o arquivo")["data"]["message_id"]


def enviar_post(cfg: dict, tk: str, paragrafos: list) -> str:
    """paragrafos: lista de linhas; cada linha é lista de elementos do 'post' do Feishu
    ({"tag": "text", "text": ..., "style": ["bold"]} ou {"tag": "img", "image_key": ...}). Devolve o message_id."""
    corpo = {"receive_id": cfg["chat_id"], "msg_type": "post",
             "content": json.dumps({"zh_cn": {"title": "", "content": paragrafos}}, ensure_ascii=False)}
    r = requests.post(f"{cfg['dominio']}/open-apis/im/v1/messages?receive_id_type=chat_id",
                      headers={"Authorization": f"Bearer {tk}"}, json=corpo, timeout=TIMEOUT)
    return _resposta(r, "envio da mensagem")["data"]["message_id"]


def texto(*partes) -> list:
    """Linha de texto. Cada parte é "texto" ou ("texto", True) para negrito."""
    linha = []
    for p in partes:
        if not isinstance(p, str) and len(p) == 3:                 # ("@", nome, id_feishu): menção
            _, nome, uid = p
            linha.append({"tag": "at", "user_id": uid} if uid else {"tag": "text", "text": f"@{nome}"})
            continue
        t, negrito = (p, False) if isinstance(p, str) else p
        el = {"tag": "text", "text": t}
        if negrito:
            el["style"] = ["bold"]
        linha.append(el)
    return linha


def enviar_relatorio(cfg: dict, itens: list, arquivo: tuple | None = None) -> str:
    """itens: ("linha", [partes...]) ou ("imagem", png_bytes), na ordem da mensagem (uma mensagem só).
    arquivo = (nome, bytes): se informado, vai logo depois, em uma segunda mensagem (o Feishu não mistura arquivo com texto)."""
    tk = token(cfg)
    chave_arquivo = subir_arquivo(cfg, tk, *arquivo) if arquivo else None      # sobe antes: se falhar, nada foi postado
    paragrafos = []
    for i, (tipo, valor) in enumerate(itens):
        if i:
            paragrafos.append(LINHA_EM_BRANCO)                 # respiro entre cada frase e cada imagem
        if tipo == "imagem":
            paragrafos.append([{"tag": "img", "image_key": subir_imagem(cfg, tk, valor)}])
        else:
            paragrafos.append(texto(*valor))
    mensagem = enviar_post(cfg, tk, paragrafos)
    if chave_arquivo:
        enviar_arquivo(cfg, tk, chave_arquivo)
    return mensagem
