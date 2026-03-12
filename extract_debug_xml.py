import zipfile
import xml.dom.minidom
import re
import os

def extract_timing(pptx_path, slide_num, out_name):
    if not os.path.exists(pptx_path):
        print(f"File not found: {pptx_path}")
        return
    with zipfile.ZipFile(pptx_path, 'r') as z:
        slide_xml_path = f'ppt/slides/slide{slide_num}.xml'
        try:
            with z.open(slide_xml_path) as f:
                content = f.read().decode('utf-8')
                m = re.search(r'<p:timing.*?</p:timing>', content, re.DOTALL)
                if m:
                    timing = m.group(0)
                    timing = timing.replace('<p:timing>', '<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">')
                    with open(out_name, 'w', encoding='utf-8') as out:
                        out.write(xml.dom.minidom.parseString(timing).toprettyxml(indent='  '))
                    print(f'Extracted {slide_xml_path} Timing to {out_name}')
                else:
                    print(f'No <p:timing> found in {slide_xml_path}')
        except KeyError:
            print(f'Slide {slide_num} not found in {pptx_path}')

extract_timing(r'C:\Users\saadk\Downloads\Jet-Orientation-Course_animated.pptx', 1, 'debug_slide1_timing.xml')
extract_timing(r'C:\Users\saadk\Downloads\Jet-Orientation-Course_animated.pptx', 2, 'debug_slide2_timing.xml')
