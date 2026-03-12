import zipfile
import xml.dom.minidom
import re

with zipfile.ZipFile(r'C:\Users\saadk\AppData\Local\Temp\native_animated_temp.pptx', 'r') as z:
    with z.open('ppt/slides/slide1.xml') as f:
        content = f.read().decode('utf-8')
        m = re.search(r'<p:timing.*?</p:timing>', content, re.DOTALL)
        if m:
            timing = m.group(0)
            # Add implicit namespaces for parsing
            timing = timing.replace('<p:timing>', '<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">')
            with open('native_timing.xml', 'w') as out:
                out.write(xml.dom.minidom.parseString(timing).toprettyxml(indent='  '))
            print("Wrote native_timing.xml")
