"""Logo no canto superior direito, sempre visível (não rola com a página).

Usa o contorno da logo (PNG transparente) como máscara e pinta com a cor certa para cada tema:
vermelho da marca no modo claro e branco no modo escuro (light-dark() segue o tema escolhido no app).
Para trocar a logo: substitua comum/assets/logo_mascara.png (PNG com fundo transparente).
"""
import base64
from pathlib import Path

ARQUIVO = Path(__file__).parent / "assets" / "logo_mascara.png"
COR_CLARO = "#E50013"          # vermelho da logo
COR_ESCURO = "#FFFFFF"
LARGURA = 280                  # px
PROPORCAO = 1000 / 214         # largura / altura da imagem


def logo_html() -> str:
    dados = base64.b64encode(ARQUIVO.read_bytes()).decode()
    altura = round(LARGURA / PROPORCAO)
    url = f"url(data:image/png;base64,{dados})"
    return f"""
<style>
/* O cabeçalho do Streamlit fica fixo no topo (com fundo sólido) e a logo é desenhada dentro dele:
   assim ela não desce com a rolagem e o conteúdo não passa por baixo dela. */
[data-testid="stHeader"] {{ position: fixed !important; top: 0; left: 0; right: 0; }}
[data-testid="stHeader"]::after {{
    content: ""; position: absolute; top: 8px; right: 6.5rem;
    width: {LARGURA}px; height: {altura}px; pointer-events: none;
    background-color: light-dark({COR_CLARO}, {COR_ESCURO});
    -webkit-mask: {url} center / contain no-repeat; mask: {url} center / contain no-repeat;
}}
@media (max-width: 900px) {{ [data-testid="stHeader"]::after {{ width: {LARGURA // 2}px; height: {altura // 2}px; right: 4rem; }} }}
</style>
"""
