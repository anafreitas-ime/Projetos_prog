import os
from qgis.core import QgsRasterLayer, QgsProject
from .DOWLOADER import Downloader


class LayerLoader:
    def __init__(self, server_url_format, destination_folder):
        self.downloader = Downloader(server_url_format, destination_folder)

    def download_raster_layer(self, file_name, progress_callback=None):
        """Baixa um arquivo raster (ex: GeoTIFF) e adiciona como camada no QGIS.

        Retorna a QgsRasterLayer adicionada, ou None em caso de falha.
        """
        file_path = self.downloader.download_file(file_name, progress_callback=progress_callback)
        if not file_path:
            return None

        layer = QgsRasterLayer(file_path, file_name)
        if not layer.isValid():
            print(f'Falha ao carregar a camada raster: {file_path}')
            return None

        QgsProject.instance().addMapLayer(layer)
        return layer

    #def download_multiple_raster_layers(self, file_names):
        """Baixa e carrega várias camadas raster (TIF) de uma vez.

        file_names: lista com os nomes dos arquivos a baixar (a pasta de
        destino já foi definida no __init__, via o Downloader interno).

        Retorna a lista das camadas carregadas com sucesso.
        """
        layers = []
        for file_name in file_names:
            layer = self.download_raster_layer(file_name)
            if layer is not None:
                layers.append(layer)
        return layers