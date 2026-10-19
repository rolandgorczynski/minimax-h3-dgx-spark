#!/usr/bin/env python3
"""Convert already downloaded FLUX.2 Klein 9B shards to native ComfyUI files.

Uses only the standard library. Tensor bytes are streamed without quantization;
Q/K/V rows are concatenated and the final AdaLN scale/shift rows are reordered.
"""
import argparse
import json
from pathlib import Path
import shutil
import struct


def read_shards(folder):
    tensors = {}
    for path in sorted(folder.glob('*.safetensors')):
        with path.open('rb') as source:
            length = struct.unpack('<Q', source.read(8))[0]
            header = json.loads(source.read(length))
        for key, value in header.items():
            if key == '__metadata__':
                continue
            if key in tensors:
                raise ValueError(f'Duplicate tensor: {key}')
            start, end = value['data_offsets']
            tensors[key] = {'dtype': value['dtype'], 'shape': value['shape'],
                            'segments': [(path, 8+length+start, end-start)]}
    if not tensors:
        raise ValueError(f'No model shards found: {folder}')
    return tensors


def flux_to_comfy(source):
    remaining = dict(source)
    result = {}
    def move(target, key):
        result[target] = remaining.pop(key)
    mapping = {
        'img_in.weight': 'x_embedder.weight', 'txt_in.weight': 'context_embedder.weight',
        'time_in.in_layer.weight': 'time_guidance_embed.timestep_embedder.linear_1.weight',
        'time_in.out_layer.weight': 'time_guidance_embed.timestep_embedder.linear_2.weight',
        'double_stream_modulation_img.lin.weight': 'double_stream_modulation_img.linear.weight',
        'double_stream_modulation_txt.lin.weight': 'double_stream_modulation_txt.linear.weight',
        'single_stream_modulation.lin.weight': 'single_stream_modulation.linear.weight',
        'final_layer.linear.weight': 'proj_out.weight',
    }
    for target, key in mapping.items():
        move(target, key)
    final = remaining.pop('norm_out.linear.weight')
    path, offset, size = final['segments'][0]
    if final['shape'][0] % 2 or size % 2:
        raise ValueError('Invalid final modulation tensor')
    result['final_layer.adaLN_modulation.1.weight'] = dict(final, segments=[
        (path, offset+size//2, size//2), (path, offset, size//2)])
    indices = sorted({int(k.split('.')[1]) for k in remaining if k.startswith('transformer_blocks.')})
    for i in indices:
        prefix = f'transformer_blocks.{i}.'
        for stream in ('img', 'txt'):
            keys = [prefix+('attn.to_'+q+'.weight' if stream == 'img' else 'attn.add_'+q+'_proj.weight')
                    for q in ('q', 'k', 'v')]
            values = [remaining.pop(key) for key in keys]
            shape = [sum(v['shape'][0] for v in values), *values[0]['shape'][1:]]
            result[f'double_blocks.{i}.{stream}_attn.qkv.weight'] = {
                'dtype': values[0]['dtype'], 'shape': shape, 'segments': sum((v['segments'] for v in values), [])}
            aliases = {
                f'{stream}_attn.proj.weight': 'attn.to_out.0.weight' if stream == 'img' else 'attn.to_add_out.weight',
                f'{stream}_attn.norm.query_norm.scale': 'attn.norm_q.weight' if stream == 'img' else 'attn.norm_added_q.weight',
                f'{stream}_attn.norm.key_norm.scale': 'attn.norm_k.weight' if stream == 'img' else 'attn.norm_added_k.weight',
                f'{stream}_mlp.0.weight': 'ff.linear_in.weight' if stream == 'img' else 'ff_context.linear_in.weight',
                f'{stream}_mlp.2.weight': 'ff.linear_out.weight' if stream == 'img' else 'ff_context.linear_out.weight',
            }
            for target, key in aliases.items():
                move(f'double_blocks.{i}.'+target, prefix+key)
    indices = sorted({int(k.split('.')[1]) for k in remaining if k.startswith('single_transformer_blocks.')})
    for i in indices:
        for target, key in {'linear1.weight': 'to_qkv_mlp_proj.weight', 'linear2.weight': 'to_out.weight',
                            'norm.query_norm.scale': 'norm_q.weight', 'norm.key_norm.scale': 'norm_k.weight'}.items():
            move(f'single_blocks.{i}.'+target, f'single_transformer_blocks.{i}.attn.'+key)
    if remaining:
        raise ValueError('Unconverted weights: '+', '.join(remaining))
    return result


def write_model(tensors, destination, source_description):
    if destination.exists():
        raise FileExistsError(f'{destination} already exists; refusing to overwrite')
    destination.parent.mkdir(parents=True, exist_ok=True)
    header = {'__metadata__': {'format': 'pt', 'source': source_description, 'conversion': 'native-comfy-bf16-v1'}}
    offset = 0
    for key, value in sorted(tensors.items()):
        size = sum(segment[2] for segment in value['segments'])
        header[key] = {'dtype': value['dtype'], 'shape': value['shape'], 'data_offsets': [offset, offset+size]}
        offset += size
    encoded = json.dumps(header, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 8)
    partial = destination.with_suffix('.safetensors.partial')
    with partial.open('wb') as output:
        output.write(struct.pack('<Q', len(encoded)))
        output.write(encoded)
        for key in sorted(tensors):
            for path, position, size in tensors[key]['segments']:
                with path.open('rb') as source:
                    source.seek(position)
                    remaining = size
                    while remaining:
                        chunk = source.read(min(16*1024*1024, remaining))
                        if not chunk:
                            raise ValueError(f'Truncated tensor: {key}')
                        output.write(chunk)
                        remaining -= len(chunk)
    if partial.stat().st_size != 8+len(encoded)+offset:
        raise ValueError('Output size mismatch')
    partial.replace(destination)
    print(f'Prepared {destination.name}: {offset/1e9:.2f} GB, {len(tensors)} tensors', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path, help='Existing FLUX.2-klein-9B snapshot directory')
    parser.add_argument('models', type=Path, help='ComfyUI models directory')
    args = parser.parse_args()
    if shutil.disk_usage(args.models).free < 36_000_000_000:
        raise SystemExit('At least 36 GB free space required')
    for directory, filename, converter, target in [
        ('transformer', 'flux-2-klein-9b-bf16.safetensors', flux_to_comfy, 'diffusion_models'),
        ('text_encoder', 'qwen_3_8b.safetensors', lambda value: value, 'text_encoders'),
    ]:
        destination = args.models/target/filename
        if destination.exists():
            print(f'Already present: {destination.name}', flush=True)
            continue
        tensors = converter(read_shards(args.snapshot/directory))
        write_model(tensors, destination, 'black-forest-labs/FLUX.2-klein-9B/'+args.snapshot.name+'/'+directory)


if __name__ == '__main__':
    main()
