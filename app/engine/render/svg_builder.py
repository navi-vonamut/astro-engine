import os
import tempfile
from kerykeion import KerykeionChartSVG

def build_natal_svg(subject) -> str:
    """
    Генерирует SVG-карту во временной папке на основе объекта AstrologicalSubject
    и возвращает ее код в виде строки.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        chart = KerykeionChartSVG(subject, chart_type="Natal", new_output_directory=tmpdir)
        chart.makeSVG()
        
        # Находим и читаем сгенерированный файл
        svg_file = [f for f in os.listdir(tmpdir) if f.endswith(".svg")][0]
        with open(os.path.join(tmpdir, svg_file), "r", encoding="utf-8") as f:
            return f.read()