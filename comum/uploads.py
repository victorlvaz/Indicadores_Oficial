"""Uploads que NÃO somem ao trocar de relatório no menu.

O file_uploader do Streamlit esvazia quando a página deixa de ser mostrada. Aqui os arquivos enviados
ficam guardados (em memória do servidor) e só saem quando você clica em ✕ ou quando o servidor é desligado.

COMPARTILHAR_ENTRE_SESSOES:
  False (padrão) -> cada navegador/aba tem os próprios arquivos; F5 na página começa do zero.
  True           -> os arquivos ficam no servidor, iguais para todos que abrirem o app e sobrevivem ao F5.
                    Use só se todos podem ver os mesmos dados (quem remover, remove para todos).
"""
import streamlit as st

COMPARTILHAR_ENTRE_SESSOES = False


class ArquivoGuardado:
    """Parecido com o arquivo do st.file_uploader: .name e .getvalue()."""

    def __init__(self, nome: str, conteudo: bytes):
        self.name = nome
        self._conteudo = conteudo

    def getvalue(self) -> bytes:
        return self._conteudo


@st.cache_resource
def _loja_servidor() -> dict:
    return {}


def _loja() -> dict:
    return _loja_servidor() if COMPARTILHAR_ENTRE_SESSOES else st.session_state.setdefault("_uploads_guardados", {})


def _tamanho(n: int) -> str:
    return f"{n / 1_000_000:.1f} MB" if n >= 1_000_000 else f"{max(n // 1000, 1)} KB"


def upload_persistente(chave: str, rotulo: str, tipos: list[str], ajuda: str | None = None) -> list[ArquivoGuardado]:
    """Uploader da barra lateral que guarda os arquivos. Devolve a lista de arquivos guardados."""
    arquivos = _loja().setdefault(chave, {})            # nome -> bytes (enviar o mesmo nome substitui)
    contador = f"_up_n_{chave}"
    n = st.session_state.get(contador, 0)

    novos = st.sidebar.file_uploader(rotulo, type=tipos, accept_multiple_files=True, help=ajuda,
                                     key=f"_up_{chave}_{n}")
    if novos:
        for f in novos:
            arquivos[f.name] = f.getvalue()
        st.session_state[contador] = n + 1             # esvazia o uploader; os arquivos já estão guardados
        st.rerun()

    for i, (nome, dados) in enumerate(list(arquivos.items())):
        c1, c2 = st.sidebar.columns([6, 1], vertical_alignment="center")
        c1.caption(f"📄 {nome} · {_tamanho(len(dados))}")
        if c2.button("✕", key=f"_rm_{chave}_{i}_{nome}", help="Remover / 移除"):
            del arquivos[nome]
            st.rerun()
    return [ArquivoGuardado(nome, dados) for nome, dados in arquivos.items()]


def manter(*chaves: str) -> None:
    """Mantém filtros, controles e abas ao trocar de relatório (o Streamlit os apaga se a página some).
    Chamar no início da página, antes de criar os widgets."""
    for k in chaves:
        if k in st.session_state:
            st.session_state[k] = st.session_state[k]


def opcao_valida(chave: str, opcoes: list) -> None:
    """Se o valor guardado de um seletor não existe mais nas opções (ex.: outro arquivo), esquece o valor."""
    if chave in st.session_state and st.session_state[chave] not in opcoes:
        del st.session_state[chave]


def esvaziar(chave: str) -> None:
    """Remove todos os arquivos guardados de um uploader (ex.: depois de salvar no banco)."""
    _loja().get(chave, {}).clear()


def remover(chave: str, nomes) -> None:
    """Remove só os arquivos citados (ex.: os que foram salvos), deixando os que deram erro para reenviar/corrigir."""
    guardados = _loja().get(chave, {})
    for n in nomes:
        guardados.pop(n, None)
