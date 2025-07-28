import xml.etree.ElementTree as ET
import re
from svgpathtools import parse_path, Path
import sys

def clean_and_scale_svg(input_path, output_path, scale=0.01):
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    tree = ET.parse(input_path)
    root = tree.getroot()

    for elem in root.findall(".//*"):
        if elem != root and 'fill' in elem.attrib:
            del elem.attrib['fill']
            elem.attrib['fill'] = "currentColor"

    del root.attrib['width']
    del root.attrib['height']
    # root.attrib['width'] = str(float(root.attrib['width'])/100)
    # root.attrib['height'] = str(float(root.attrib['height'])/100)  

    tree.write(output_path, encoding='utf-8', xml_declaration=False)
    # print(root)
    print(f"Cleaned and scaled SVG saved to {output_path}")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python clean_scale_svg.py input.svg output.svg [scale]")
    else:
        scale_val = float(sys.argv[3]) if len(sys.argv) == 4 else 0.01
        clean_and_scale_svg(sys.argv[1], sys.argv[2], scale=scale_val)
