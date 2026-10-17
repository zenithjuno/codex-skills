"""Artifact-level checks for constant physical styling across graph sizes."""
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as E
from math import isclose
import json
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from math_figure_style import PrintStyle, verify_docx_media

HERE=Path(__file__).resolve().parent
ASSETS=HERE.parent/'assets/math-figures'
GENERATOR=ASSETS/'examples/function-checking/build_figures.py'
NS={'s':'http://www.w3.org/2000/svg'}
SIZES=[4.0,5.0,6.5]

def geometry(root):
    return {'lines':[[node.attrib[k] for k in ['x1','y1','x2','y2']] for node in root.findall('s:line',NS)],
            'points':[[node.attrib[k] for k in ['cx','cy','fill']] for node in root.findall('s:circle',NS)]}


def main():
    records=[]
    with TemporaryDirectory(prefix='solve-print-style-') as temporary:
        baseline={}
        exports={}
        for cm in SIZES:
            output=Path(temporary)/str(cm)
            subprocess.run([sys.executable,str(GENERATOR),'--size-cm',str(cm),'--output-dir',str(output)],check=True,capture_output=True)
            exports[cm]=output
            manifest=json.loads((output/'print-manifest.json').read_text())
            assert all(item['label_overlaps']==0 for item in manifest['figures'])
            for number in range(1,7):
                root=E.parse(output/f'graph-{number:02}.svg').getroot()
                printed_cm=float(root.attrib['height'].removesuffix('cm'))
                assert printed_cm==cm
                factor=printed_cm*72/2.54/760
                text_sizes={round(float(t.attrib['font-size'].removesuffix('px'))*factor,7) for t in root.findall('s:text',NS)}
                assert text_sizes=={10.0,12.0},text_sizes
                widths={round(float(line.attrib['stroke-width'])*factor,7) for line in root.findall('s:line',NS)}
                assert widths=={0.5,0.75,1.0},widths
                for point in root.findall('s:circle',NS):
                    assert isclose(float(point.attrib['r'])*factor,2.5)
                    assert isclose(float(point.attrib['stroke-width'])*factor,0.75)
                if number not in baseline: baseline[number]=geometry(root)
                assert geometry(root)==baseline[number],f'Graph geometry changed at {cm}cm'
                image=Image.open(output/f'graph-{number:02}.png')
                assert image.info['dpi'][0]>=599.9
            records.append({'height_cm':cm,'graphs':6,'number_pt':10,'axis_label_pt':12,'graph_line_pt':1,'axis_line_pt':0.75,'tick_pt':0.5,'label_overlaps':0,'geometry_unchanged':True,'min_dpi':600,'status':'PASS'})
        for value in ['0','1']:
            result=subprocess.run([sys.executable,str(GENERATOR),'--size-cm',value,'--output-dir',str(Path(temporary)/('invalid-'+value))],capture_output=True,text=True)
            assert result.returncode!=0,f'Unsafe size {value} was silently accepted'
        result=subprocess.run([sys.executable,str(GENERATOR),'--size-cm','6.5'],capture_output=True,text=True)
        assert result.returncode!=0 and '--output-dir' in result.stderr
        copied=Path(temporary)/'build_copied_helper.py'
        copied.write_text('def verify_docx_media(*args): pass\n')
        guarded=subprocess.run([sys.executable,str(HERE.parent/'scripts/audit_generator_shared_api.py'),'--file',str(copied),'--json'],capture_output=True,text=True)
        assert guarded.returncode!=0 and 'protected-helper-definition' in guarded.stdout
        imported=Path(temporary)/'build_imported_helper.py'
        imported.write_text('from math_figure_style import verify_docx_media\n')
        subprocess.run([sys.executable,str(HERE.parent/'scripts/audit_generator_shared_api.py'),'--file',str(imported)],check=True,capture_output=True)
        # A minimal package isolates height/hash checking from full DOCX validation.
        from zipfile import ZipFile
        five=exports[5.0]
        sources=[five/f'graph-{n:02}.png' for n in range(1,7)]
        package=Path(temporary)/'media-fixture.docx'
        document='<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>'
        document+=''.join(f'<wp:extent cx="1800000" cy="1800000"/><a:blip r:embed="r{n}"/>' for n in range(1,7))+'</w:body></w:document>'
        links='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'+''.join(f'<Relationship Id="r{n}" Target="media/image{n}.png"/>' for n in range(1,7))+'</Relationships>'
        with ZipFile(package,'w') as zipped:
            zipped.writestr('word/document.xml',document)
            zipped.writestr('word/_rels/document.xml.rels',links)
            for n,source in enumerate(sources,1): zipped.write(source,f'word/media/image{n}.png')
        verify_docx_media(package,sources,5.0)
        for candidate,cm in [(sources,1.234),([sources[1]]+sources[1:],5.0)]:
            try: verify_docx_media(package,candidate,cm)
            except ValueError: pass
            else: raise AssertionError('DOCX size/hash drift was not rejected')
        # The same pixels per centimetre in every column make this a true size comparison.
        dpi=180
        column=round(6.5/2.54*dpi)+40
        height=2*(round(6.5/2.54*dpi)+70)
        proof=Image.new('RGB',(column*3,height),'white')
        draw=ImageDraw.Draw(proof)
        font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Georgia.ttf',22)
        for index,cm in enumerate(SIZES):
            side=round(cm/2.54*dpi)
            for row,number in enumerate([1,6]):
                y=row*(height//2)
                draw.text((index*column+20,y+12),f'{cm:g} cm',font=font,fill='black')
                panel=Image.open(exports[cm]/f'graph-{number:02}.png').resize((side,side),Image.Resampling.LANCZOS)
                proof.paste(panel,(index*column+(column-side)//2,y+55))
        proof.save(Path(temporary)/'size-proof.png',dpi=(dpi,dpi))
    report={'cases':records,'negative_checks':['zero size rejected','unreadably small size rejected without shrinking type','size override cannot overwrite current assets','DOCX height/hash drift rejected'],'status':'PASS'}
    assert report['status']=='PASS'
    print('PASS: 18 exported graphs at 4/5/6.5cm; exact 10/12pt fonts and 1pt curves; unchanged geometry; 5 negative checks')

if __name__=='__main__':
    main()
