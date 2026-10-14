"""Logo no canto superior direito.

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
.logo-canto {{
    position: fixed; top: 8px; right: 6.5rem; z-index: 999991;
    width: {LARGURA}px; height: {altura}px; pointer-events: none;
    background-color: light-dark({COR_CLARO}, {COR_ESCURO});
    -webkit-mask: {url} center / contain no-repeat; mask: {url} center / contain no-repeat;
}}
@media (max-width: 900px) {{ .logo-canto {{ width: {LARGURA // 2}px; height: {altura // 2}px; right: 4rem; }} }}
</style>
<div class="logo-canto" role="img" aria-label="J&T Express"></div>
"""
