"""
Quadrículas Disponíveis — TOPODATA
Mostra, num mapa com fundo OpenStreetMap, todas as quadrículas do TOPODATA/INPE
disponíveis para download (mesma fonte de dados do plugin TOPODATA_Dowloader:
API STAC em data.inpe.br). Cada quadrícula aparece com seu código visível no
mapa. É só uma visualização, pra ajudar o usuário a escolher visualmente.

Como rodar:
    pixi add python streamlit folium streamlit-folium requests
    pixi shell
    streamlit run app_seletor_quadriculas.py
"""

# requests: faz as chamadas HTTP na API do STAC
# streamlit: biblioteca do app em si
# folium: monta o mapa interativo
# st_folium: ponte que exibe o mapa do folium dentro do Streamlit
import requests
import streamlit as st
import folium
from streamlit_folium import st_folium

# URL base da API do TOPODATA/INPE, a mesma que o DOWLOADER.py do plugin usa
STAC_COLLECTION_URL = "https://data.inpe.br/bdc/stac/v1/collections/topodata-1/items"


# ---------------------------------------------------------------------------
# Busca de todas as quadrículas (id + geometria) na API STAC, com paginação
# ---------------------------------------------------------------------------

# @st.cache_data(persist="disk", ...) guarda o resultado em disco, então essa
# função só busca tudo na API de verdade na primeira vez — depois disso, o
# Streamlit reaproveita o que já foi buscado.
@st.cache_data(persist="disk", show_spinner="Carregando quadrículas da API STAC...")
def carregar_quadriculas() -> list[dict]:
    itens = []
    # A API devolve os resultados em páginas de 100 itens por vez
    url = f"{STAC_COLLECTION_URL}?limit=100"

    # Fica repetindo a busca até não haver mais próxima página
    while url:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # Percorre cada quadrícula da página atual
        for feature in data.get("features", []):
            if "ZN" not in feature.get("assets", {}):
                continue
            itens.append({
                "id": feature["id"],          # código da quadrícula
                "geometry": feature["geometry"],  # contorno real (polígono)
                "bbox": feature["bbox"],      # retângulo simples [oeste, sul, leste, norte]
            })

        # Procura no array "links" da resposta um link com "rel": "next";
        # se não existir, url vira None e o laço para
        url = next(
            (link["href"] for link in data.get("links", []) if link.get("rel") == "next"),
            None,
        )

    return itens


def centro_bbox(bbox: list[float]) -> list[float]:
    """Calcula o centro [lat, lon] de um bbox [minx, miny, maxx, maxy]."""
    # Tira a média entre oeste/leste e entre sul/norte para achar o ponto
    # central da quadrícula — é aí que o código dela vai ser escrito no mapa
    minx, miny, maxx, maxy = bbox
    return [(miny + maxy) / 2, (minx + maxx) / 2]


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

# Configura o título da aba do navegador e os textos do topo da página
st.set_page_config(page_title="Quadrículas TOPODATA", layout="wide")
st.title("Quadrículas Disponíveis — TOPODATA")
st.caption("Passe o mouse numa quadrícula pra ver o código, ou veja o número direto no mapa.")

# Busca os dados (usando o cache, se já existir) e mostra quantos foram encontrados
quadriculas = carregar_quadriculas()
st.write(f"{len(quadriculas)} quadrículas disponíveis.")

# Cria o mapa centralizado no Brasil, sem nenhum fundo fixo — os fundos são
# adicionados logo abaixo, como camadas separadas que o usuário pode alternar
mapa = folium.Map(location=[-15, -55], zoom_start=4, tiles=None)

# Fundo 1: OpenStreetMap (mapa de ruas padrão)
folium.TileLayer(tiles="OpenStreetMap", name="OpenStreetMap").add_to(mapa)

# Fundo 2: OpenTopoMap (mapa topográfico, com relevo e curvas de nível —
# combina bem com dados de altitude como os do TOPODATA)
folium.TileLayer(
    tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    attr=(
        'Map data: &copy; OpenStreetMap contributors, SRTM | '
        'Map style: &copy; OpenTopoMap (CC-BY-SA)'
    ),
    name="OpenTopoMap",
).add_to(mapa)

# Agrupa todos os polígonos e rótulos das quadrículas num único grupo, com
# control=False, pra eles NÃO aparecerem como 556 itens separados na lista
# do controle de camadas — só os fundos (OpenStreetMap/OpenTopoMap) aparecem lá.
grupo_quadriculas = folium.FeatureGroup(name="Quadrículas", control=False)
grupo_quadriculas.add_to(mapa)

# Para cada quadrícula, desenha o polígono da área e o rótulo com o código
for q in quadriculas:
    feature = {
        "type": "Feature",
        "geometry": q["geometry"],
        "properties": {"id": q["id"]},
    }

    # Desenha o polígono real da área (contorno azul, preenchimento bem leve)
    # e mostra o código como tooltip ao passar o mouse
    folium.GeoJson(
        feature,
        tooltip=folium.GeoJsonTooltip(fields=["id"], aliases=["Quadrícula:"]),
        style_function=lambda _: {"color": "#2b6cb0", "weight": 1, "fillColor": "#63b3ed", "fillOpacity": 0.12},
        highlight_function=lambda _: {"fillOpacity": 0.5},
    ).add_to(grupo_quadriculas)

    # Fixa um texto com o código da quadrícula no centro dela, visível direto
    # no mapa (sem precisar passar o mouse). pointer-events:none evita que
    # esse texto bloqueie o clique/hover no polígono que está embaixo dele
    centro = centro_bbox(q["bbox"])
    folium.map.Marker(
        centro,
        icon=folium.DivIcon(html=(
            '<div style="font-size:8px; color:#1a365d; text-align:center; '
            'white-space:nowrap; pointer-events:none;">' + q["id"] + "</div>"
        )),
    ).add_to(grupo_quadriculas)

# Adiciona o controle (aquele ícone de camadas no canto do mapa) que deixa o
# usuário escolher entre os fundos cadastrados acima
folium.LayerControl().add_to(mapa)

# Desenha o mapa montado na tela. Não guardamos o retorno dessa chamada:
# o app não reage a cliques, é só uma exibição estática do mapa.
st_folium(mapa, height=650, use_container_width=True)