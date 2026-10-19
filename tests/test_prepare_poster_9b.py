"""Local checkpoint conversion preserves bytes and required tensor row ordering."""
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1]/'scripts/prepare_poster_9b.py'
spec = importlib.util.spec_from_file_location('prepare_9b', SOURCE)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class Prepare9BTests(unittest.TestCase):
    def test_shards_join_and_modulation_swap_preserve_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root/'shards'
            source.mkdir()
            direct = {
                'x_embedder.weight': [1.0], 'context_embedder.weight': [2.0],
                'time_guidance_embed.timestep_embedder.linear_1.weight': [3.0],
                'time_guidance_embed.timestep_embedder.linear_2.weight': [4.0],
                'double_stream_modulation_img.linear.weight': [5.0],
                'double_stream_modulation_txt.linear.weight': [6.0],
                'single_stream_modulation.linear.weight': [7.0], 'proj_out.weight': [8.0],
                'norm_out.linear.weight': [10.0, 20.0],
            }
            for i, (key, values) in enumerate(direct.items()):
                data = struct.pack('<'+'f'*len(values), *values)
                header = json.dumps({key: {'dtype': 'F32', 'shape': [len(values), 1], 'data_offsets': [0, len(data)]}}).encode()
                (source/f'{i}.safetensors').write_bytes(struct.pack('<Q',len(header))+header+data)
            tensors = prepare.flux_to_comfy(prepare.read_shards(source))
            destination = root/'model.safetensors'
            prepare.write_model(tensors, destination, 'test')
            with destination.open('rb') as stream:
                size = struct.unpack('<Q',stream.read(8))[0]
                header = json.loads(stream.read(size))
                offset = header['final_layer.adaLN_modulation.1.weight']['data_offsets'][0]
                stream.seek(8+size+offset)
                self.assertEqual(struct.unpack('<ff',stream.read(8)), (20.0,10.0))
            with self.assertRaises(FileExistsError):
                prepare.write_model(tensors, destination, 'test')

    def test_unknown_tensor_is_not_silently_dropped(self):
        # Missing known keys is also an error: partial checkpoints must not be accepted.
        with self.assertRaises(KeyError):
            prepare.flux_to_comfy({'unknown.weight': {}})

    def test_qkv_rows_join_in_query_key_value_order(self):
        names = [
            'x_embedder.weight', 'context_embedder.weight',
            'time_guidance_embed.timestep_embedder.linear_1.weight',
            'time_guidance_embed.timestep_embedder.linear_2.weight',
            'double_stream_modulation_img.linear.weight', 'double_stream_modulation_txt.linear.weight',
            'single_stream_modulation.linear.weight', 'proj_out.weight', 'norm_out.linear.weight',
            'transformer_blocks.0.attn.to_out.0.weight', 'transformer_blocks.0.attn.to_add_out.weight',
            'transformer_blocks.0.attn.norm_q.weight', 'transformer_blocks.0.attn.norm_k.weight',
            'transformer_blocks.0.attn.norm_added_q.weight', 'transformer_blocks.0.attn.norm_added_k.weight',
            'transformer_blocks.0.ff.linear_in.weight', 'transformer_blocks.0.ff.linear_out.weight',
            'transformer_blocks.0.ff_context.linear_in.weight', 'transformer_blocks.0.ff_context.linear_out.weight',
        ]
        names += ['transformer_blocks.0.attn.'+prefix+'.weight' for prefix in
                  ('to_q', 'to_k', 'to_v', 'add_q_proj', 'add_k_proj', 'add_v_proj')]
        source = {name: {'dtype': 'BF16', 'shape': [2, 2], 'segments': [(Path(name), 0, 8)]} for name in names}
        result = prepare.flux_to_comfy(source)
        for stream, keys in [('img', ['to_q', 'to_k', 'to_v']), ('txt', ['add_q_proj', 'add_k_proj', 'add_v_proj'])]:
            tensor = result[f'double_blocks.0.{stream}_attn.qkv.weight']
            self.assertEqual(tensor['shape'], [6, 2])
            self.assertEqual([segment[0].name for segment in tensor['segments']],
                             ['transformer_blocks.0.attn.'+key+'.weight' for key in keys])
