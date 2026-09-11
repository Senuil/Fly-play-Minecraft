"""Import Shiu v783 tables without rounding 64-bit FlyWire root IDs.

Supports full graph, explicit induced subset, and explicitly non-anatomical
six-neuron connectivity probe. No guessed neurotransmitter signs.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import sparse


def digest(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_bundle(output, ids, pre, post, signed_counts, metadata):
    output = Path(output)
    if output.exists():
        raise ValueError("output already exists; choose a new directory")
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError("IDs must be nonempty and unique")
    pre, post, weights = np.asarray(pre), np.asarray(post), np.asarray(signed_counts, dtype=np.float32)
    if pre.dtype.kind not in 'iu' or post.dtype.kind not in 'iu':
        raise ValueError("indices must be integers")
    if len(pre) != len(post) or len(pre) != len(weights) or not np.isfinite(weights).all():
        raise ValueError("invalid edge arrays")
    if np.any(pre < 0) or np.any(post < 0) or np.any(pre >= len(ids)) or np.any(post >= len(ids)):
        raise ValueError("edge index outside neuron table")
    w = sparse.coo_matrix((weights*0.275, (post, pre)), shape=(len(ids), len(ids))).tocsr()
    w.eliminate_zeros()
    output.mkdir(parents=True)
    sparse.save_npz(output / 'weights.npz', w)
    (output / 'ids.json').write_text(json.dumps(ids))
    metadata = {**metadata, 'orientation': 'post,pre', 'weight_unit': 'mV',
                'synapse_gain_mV': 0.275, 'neurons': len(ids), 'edges': w.nnz}
    (output / 'metadata.json').write_text(json.dumps(metadata, indent=2))
    return w


def main():
    import pyarrow.parquet as pq
    parser = argparse.ArgumentParser()
    parser.add_argument('--completeness', required=True)
    parser.add_argument('--connectivity', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--dataset-version', default='FlyWire-783-Shiu')
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--ids', help='JSON list of string root IDs; retain all induced edges')
    selection.add_argument('--probe', action='store_true', help='Six real neurons, artificial I/O mapping')
    args = parser.parse_args()
    with open(args.completeness, newline='') as f:
        rows = csv.reader(f)
        next(rows)  # Upstream uses CSV index column as FlyWire root ID.
        ids = [row[0] for row in rows]
    if not all(x.isdecimal() for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('first CSV column must contain unique integer root IDs')
    table = pq.read_table(args.connectivity, columns=[
        'Presynaptic_Index', 'Postsynaptic_Index', 'Excitatory x Connectivity'])
    pre, post, weights = [table[c].to_numpy() for c in table.column_names]
    if pre.dtype.kind not in 'iu' or post.dtype.kind not in 'iu' or not np.isfinite(weights).all():
        raise ValueError('invalid upstream columns')
    if np.any(pre < 0) or np.any(post < 0) or np.any(pre >= len(ids)) or np.any(post >= len(ids)):
        raise ValueError('completeness and connectivity tables do not match')
    metadata = {'dataset_version': args.dataset_version,
        'source': 'https://github.com/philshiu/Drosophila_brain_model',
        'source_sha256': {'completeness': digest(args.completeness), 'connectivity': digest(args.connectivity)},
        'selection': 'full', 'dynamics': 'experimental Euler LIF; not validated paper reproduction'}
    mapping = None
    if args.probe:
        # Select three disjoint strong excitatory pairs that have no cross-pair edges.
        # This is an engineering probe, not an identified sensory/motor circuit.
        graph = sparse.coo_matrix((weights, (post, pre)), shape=(len(ids), len(ids))).tocsr()
        used, pairs = set(), []
        for edge in np.argsort(-weights):
            a, b = int(pre[edge]), int(post[edge])
            if a == b or a in used or b in used or weights[edge] < 220:
                continue
            if used:
                old = list(used)
                if graph[[a,b]][:,old].nnz or graph[old][:,[a,b]].nnz:
                    continue
            used.update((a,b)); pairs.append((a,b))
            if len(pairs) == 3:
                break
        if len(pairs) != 3:
            raise ValueError('could not find independent probe pairs')
        chosen = sorted(used)
        mapping = {'dataset_version': args.dataset_version,
            'interpretation': 'ARTIFICIAL I/O on real induced edges; no anatomical motor claim',
            'inputs': {'drive': [ids[pairs[0][0]]], 'obstacle_left': [ids[pairs[1][0]]], 'obstacle_right': [ids[pairs[2][0]]]},
            'outputs': {'forward': [ids[pairs[0][1]]], 'turn_right': [ids[pairs[1][1]]], 'turn_left': [ids[pairs[2][1]]]}}
        metadata['selection'] = 'six-neuron non-anatomical connectivity probe; all induced edges retained'
    elif args.ids:
        requested = json.loads(Path(args.ids).read_text())
        if not isinstance(requested, list) or not requested or any(not isinstance(x,str) for x in requested):
            raise ValueError('IDs must be a nonempty JSON list of strings')
        lookup = {x:i for i,x in enumerate(ids)}
        chosen = sorted({lookup[x] for x in requested})
        metadata['selection'] = 'explicit induced subgraph'
    else:
        chosen = None
    if chosen is not None:
        remap = np.full(len(ids), -1, dtype=np.int32)
        remap[chosen] = np.arange(len(chosen))
        mask = (remap[pre] >= 0) & (remap[post] >= 0)
        pre, post, weights = remap[pre[mask]], remap[post[mask]], weights[mask]
        ids = [ids[i] for i in chosen]
    w = write_bundle(args.output, ids, pre, post, weights, metadata)
    if mapping:
        (Path(args.output)/'mapping.json').write_text(json.dumps(mapping, indent=2))
    print(json.dumps({'neurons':len(ids), 'edges':w.nnz, 'selection':metadata['selection']}))


if __name__ == '__main__':
    main()
