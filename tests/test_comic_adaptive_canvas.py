"""Canvas-Felder müssen tatsächlich unterschiedliche Formate bis zum Renderer erhalten."""
import copy,io,json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'automation/comics'))
from panel_formats import apply,sizes
from lettering import DESIGN,LAYOUT
from engine import Engine,validate_request
from storage import Store
import guided_reader

class AdaptiveCanvasTests(unittest.TestCase):
    def test_all_templates_have_bounded_formats_and_large_fields_get_more_pixels(self):
        for template in LAYOUT.TEMPLATES:
            if template=='standard':continue
            for size in sizes(template):DESIGN.validate_canvas_size(size);DESIGN.validate_render_size(DESIGN.art_render_size(size,'Ein kurzer Text.'))
        formats=sizes('hero_top');self.assertGreater(formats[0][0],formats[1][0]);self.assertGreater(formats[0][1],formats[1][1])
        formats=sizes('four_alternate');self.assertGreater(formats[0][0]/formats[0][1],formats[1][0]/formats[1][1])
        self.assertGreater(sizes('four_strips')[0][0]/sizes('four_strips')[0][1],3)

    def test_preparation_preserves_story_words_and_moves_bubbles_below_caption(self):
        scenes=[{'story':'Hildebrand bleibt im Sattel.','dialog':'Der Reiter spricht.','characters':['a'*32],'bubbles':[{'speaker':'a'*32,'text':'Nein!'}]}]*4;before=copy.deepcopy(scenes)
        adapted=apply(scenes,'four_alternate');self.assertEqual(scenes,before)
        for old,new in zip(before,adapted):
            self.assertEqual(old['story'],new['story']);self.assertEqual(old['dialog'],new['dialog']);self.assertEqual(new['bubbles'][0]['text'],'Nein!')
            self.assertGreaterEqual(new['bubbles'][0]['y'],DESIGN.caption_band(new['dialog'],new['canvas_size'])/new['canvas_size'][1])
        self.assertEqual(apply(adapted,'four_alternate'),adapted)
        normal=apply(adapted,'standard');self.assertTrue(all('canvas_size' not in s and 'render_size' not in s for s in normal))

    def test_composed_cells_are_filled_and_reader_uses_same_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);scenes=apply([{'story':'Eine Szene.','dialog':'','characters':[],'bubbles':[]} for _ in range(4)],'four_alternate');tiles=[];paths=[]
            for i,scene in enumerate(scenes):
                art=Image.new('RGB',tuple(scene['render_size']),(30+i*30,90,140));tile=DESIGN.panel(art,'',i+1,[],canvas_size=scene['canvas_size']);path=root/f'{i:02}.png';tile.save(path);paths.append(path);tiles.append(tile)
                self.assertEqual(tile.size,tuple(scene['canvas_size']))
            geometry=LAYOUT.template_geometry([t.size for t in tiles],'four_alternate',adaptive=True)
            for r in geometry['regions']:
                x,y,w,h=r['rect'];left,top,right,bottom=r['box'];self.assertEqual(w,right-left-4);self.assertEqual(h,bottom-top-4)
            source={'title':'Vier Formate','page_template':'four_alternate','scenes':scenes}
            reader=guided_reader.pages_for(source,paths)[0];self.assertTrue(reader['adaptive']);self.assertEqual(reader['regions'],[{**r,'panel':i+1,'ordinal':i+1} for i,r in enumerate(geometry['regions'])])
            page=guided_reader.render_page(source,paths,reader);page.save('/tmp/comic-adaptive-canvas-test.png');self.assertEqual(page.size,(geometry['width'],geometry['height']))
            for i,r in enumerate(reader['regions']):
                x,y,w,h=r['rect'];self.assertEqual(page.getpixel((x+w//2,y+h//2)),(30+i*30,90,140))

    def test_graph_receives_new_formats_instead_of_old_fixed_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(tmp);ident='c'*32;store.create(ident,validate_request({'kacheln':4,'page_template':'four_alternate'}));graphs=[]
            class Client:
                def run(self,job,step,graph,workflow):graphs.append(graph);return {next(k for k,v in graph.items() if v['class_type']=='DGXComicStudio'):{'comic_panels':[]}}
            engine=Engine(store,Client(),ROOT/'examples/comics/workflows/04_Comic_Automat_9B.json','unused','unused')
            engine.studio(ident,'test',{'story':'Eine Geschichte.','title':'Formate'},[],{'scenes':[{'story':'Ein Raum.','dialog':'','characters':[],'bubbles':[]} for _ in range(4)]})
            node=graphs[0][engine.node]['inputs'];planned=json.loads(node['bearbeiteter_plan'])['scenes']
            self.assertNotEqual(planned[0]['render_size'],planned[1]['render_size']);self.assertNotEqual(planned[0]['canvas_size'],planned[1]['canvas_size'])

    def test_added_narrator_preserves_entire_art_instead_of_cropping_heads(self):
        from PIL import ImageChops,ImageDraw,ImageOps
        raw=Image.new('RGB',(1296,800),'#555555');draw=ImageDraw.Draw(raw)
        draw.rectangle((0,0,1295,35),fill='red');draw.rectangle((0,765,1295,799),fill='blue')
        size=(1088,672);caption='Ein Anflug';band=DESIGN.caption_band(caption,size)
        self.assertEqual(band,80);self.assertEqual(DESIGN.caption_font(size),28)
        tile=DESIGN.panel(raw,caption,4,[],canvas_size=size)
        expected=ImageOps.contain(raw,(1076,672-band-12),Image.Resampling.LANCZOS)
        left=6+(1076-expected.width)//2;top=band+6+(672-band-12-expected.height)//2
        self.assertIsNone(ImageChops.difference(tile.crop((left,top,left+expected.width,top+expected.height)),expected).getbbox())
        self.assertGreater(DESIGN.caption_band('Ein längerer Erzählertext. '*12,size),band)

    def test_long_text_in_thin_panel_is_rejected_instead_of_shrunk(self):
        size=sizes('four_strips')[0]
        caption=('Der Reiter kommt näher und spricht mit seinem Sohn. Beide hören aufmerksam zu und halten einen Moment inne, bevor sie antworten. ')*3
        DESIGN.panel(Image.new('RGB',(1024,704)),caption,1,[])
        with self.assertRaises(ValueError):DESIGN.panel(Image.new('RGB',(1024,704)),caption,1,[],canvas_size=size)

if __name__=='__main__':unittest.main()
