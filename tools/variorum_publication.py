"""Independent Python projection of frozen Variorum revisions for publication.

This module reads trusted captured inputs only. It never rewrites source or
accepts browser materialized text as proof of source freshness.
"""
from copy import deepcopy
import hashlib
import json
import re


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(piece, version, members, lines):
    payload = {'pieceId': piece, 'versionId': version, 'members': members,
               'lines': [{k: l[k] for k in ('lineId', 'text', 'blockType', 'breakBefore') if k in l} for l in lines]}
    return 'sha256:' + hashlib.sha256(canonical(payload).encode()).hexdigest()


def transform_case(text, mode):
    if mode == 'asis':
        return text
    if mode == 'lower':
        return text.lower()
    if mode == 'upper':
        return text.upper()
    if mode == 'sentence':
        return '\n'.join(re.sub(r'^(\s*)(\S)(.*)$', lambda m: m[1] + m[2].upper() + m[3].lower(), line) for line in text.split('\n'))
    raise ValueError('invalid_case')


def catalog(source, db):
    reviews = {**source.get('review', {}).get('acceptedReviews', {}), **db.get('reviews', {})}
    pages = {p['id']: p for p in source['review']['pages']}
    versions = {}
    for piece in source['j']['pieces']:
        for version in piece['V']:
            lines = []
            available = True
            for page_id, blocks in version['P']:
                for bi in blocks:
                    b = pages[page_id]['blocks'][bi]
                    for li, l in enumerate(b['lines']):
                        review = reviews.get(l['id'], {})
                        text = l['tx']
                        if b.get('t') != 'quotation' and review.get('status') == 'corrected':
                            if review.get('original') != text or not isinstance(review.get('text'), str):
                                available = False
                            else:
                                text = review['text']
                        if l.get('transcriptionStatus') == 'untranscribed':
                            available = False
                        lines.append({'lineId': l['id'], 'text': text, 'originalText': l['tx'],
                                      'pageId': page_id, 'blockIndex': bi, 'blockType': b.get('t') or 'text',
                                      'breakBefore': l.get('breakBefore', bool(lines) and li == 0),
                                      'verified': review.get('status') in ('confirmed', 'corrected') and review.get('original') == l['tx']})
            versions[version['id']] = {'pieceId': piece['id'], 'versionId': version['id'], 'lines': lines,
                                      'available': available and bool(lines), 'kind': 'journal',
                                      'sourceFingerprint': fingerprint(piece['id'], version['id'], version['P'], lines),
                                      'exposures': deepcopy(version.get('exposures', version.get('exposure', [])))}
    supplement = source.get('variorumSupplement', {'schemaVersion': 1, 'sources': []})
    if supplement.get('schemaVersion') != 1 or not isinstance(supplement.get('sources'), list):
        raise ValueError('invalid_supplement')
    for s in supplement['sources']:
        if s['versionId'] in versions or s['kind'] not in ('lyric', 'notebook') or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', s['versionId']):
            raise ValueError('duplicate_or_invalid_source')
        if s['pieceId'] not in {p['id'] for p in source['j']['pieces']}:
            raise ValueError('unknown_source_piece')
        v = deepcopy(s)
        seen = set()
        for line in v.get('lines', []):
            if not isinstance(line.get('lineId'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', line['lineId']) or line['lineId'] in seen or not isinstance(line.get('text'), str) or type(line.get('breakBefore')) is not bool:
                raise ValueError('invalid_source_line')
            seen.add(line['lineId'])
        for line in v.get('lines', []):
            review = reviews.get(line['lineId'], {})
            line['originalText'] = line.get('originalText', line['text'])
            line['blockType'] = line.get('blockType') or 'text'
            line['verified'] = review.get('status') in ('confirmed', 'corrected') and review.get('original') == line['originalText']
            if review.get('status') == 'corrected' and line['verified']:
                if not isinstance(review.get('text'), str):
                    raise ValueError('invalid_review')
                line['text'] = review['text']
        v['available'] = bool(v.get('lines')) and v.get('status') != 'text-not-supplied'
        v['sourceFingerprint'] = fingerprint(v['pieceId'], v['versionId'], [], v.get('lines', []))
        v['exposures'] = []
        for exposure in [*s.get('exposures', []), *db.get('release', {}).get(v['pieceId'], {}).get('exposures', [])]:
            if exposure not in v['exposures']:
                v['exposures'].append(deepcopy(exposure))
        versions[v['versionId']] = v
    for v in versions.values():
        exposures = [*v.get('exposures', []), *db.get('release', {}).get(v['pieceId'], {}).get('exposures', [])]
        for key, item in db.get('versions', {}).items():
            if key == v['versionId'] or item.get('versionId') == v['versionId']:
                exposures.extend(item.get('exposures', item.get('exposure', [])))
        v['exposures'] = []
        for exposure in exposures:
            if exposure not in v['exposures']:
                v['exposures'].append(deepcopy(exposure))
    return versions


def validate_parts(versions, parts):
    if not parts or parts.get('pieceId') not in {v['pieceId'] for v in versions.values()}:
        raise ValueError('unknown_piece')
    declared = parts.get('parts')
    order = parts.get('canonicalOrder')
    links = parts.get('linkedPieces')
    if not isinstance(declared, list) or not isinstance(order, list) or not isinstance(links, list):
        raise ValueError('invalid_parts')
    ids = [p['id'] for p in declared]
    if len(set(ids)) != len(ids) or len(set(order)) != len(ids) or set(order) != set(ids):
        raise ValueError('invalid_canonical_order')
    if len(set(links)) != len(links) or parts['pieceId'] in links or not set(links).issubset({v['pieceId'] for v in versions.values()}):
        raise ValueError('invalid_linked_pieces')
    for version_id, mapping in parts.get('maps', {}).items():
        v = versions.get(version_id)
        if not v or v['pieceId'] not in [parts['pieceId'], *links]:
            raise ValueError('invalid_version_membership')
        used, keys = set(), set()
        positions = {l['lineId']: i for i, l in enumerate(v['lines'])}
        for part, occurrences in mapping.get('segments', {}).items():
            if part not in ids or not isinstance(occurrences, list):
                raise ValueError('invalid_segment')
            for o in occurrences:
                number = o.get('occurrence')
                if type(number) is not int or not 0 < number <= 9007199254740991 or (part, number) in keys or not o.get('lines'):
                    raise ValueError('invalid_occurrence')
                keys.add((part, number))
                previous = None
                for lid in o['lines']:
                    current = positions.get(lid)
                    if current is None or lid in used or (previous is not None and current != previous + 1):
                        raise ValueError('missing_duplicate_or_noncontiguous_line')
                    used.add(lid); previous = current
                if type(o.get('accepted')) is not bool:
                    raise ValueError('missing_acceptance')
        sequence = [(o['partId'], o['occurrence']) for o in mapping.get('version_part_order', [])]
        if len(sequence) != len(keys) or len(set(sequence)) != len(keys) or set(sequence) != keys:
            raise ValueError('invalid_version_part_order')


def materialize(versions, parts, recipe, mode):
    if not parts or not recipe:
        raise ValueError('parts_revision_missing')
    validate_parts(versions, parts)
    snapshots, lines, exposures = [], [], []
    recipe_keys = set()
    for si, step in enumerate(recipe):
        key = (step['partId'], step['occurrence'])
        if key in recipe_keys:
            raise ValueError('duplicate_recipe_occurrence')
        recipe_keys.add(key)
        v = versions.get(step['from'])
        if not v or not v['available'] or v['kind'] == 'composite':
            raise ValueError('source_unavailable')
        if v['pieceId'] not in [parts['pieceId'], *parts.get('linkedPieces', [])]:
            raise ValueError('invalid_version_membership')
        occurrences = parts['maps'].get(step['from'], {}).get('segments', {}).get(step['partId'], [])
        occurrence = next((o for o in occurrences if o['occurrence'] == step['occurrence']), None)
        if not occurrence or occurrence.get('accepted') is not True:
            raise ValueError('unaccepted_or_missing_occurrence')
        by_id = {l['lineId']: l for l in v['lines']}
        try:
            selected = [deepcopy(by_id[lid]) for lid in occurrence['lines']]
        except KeyError as e:
            raise ValueError('missing_source_line') from e
        positions = [next(i for i, l in enumerate(v['lines']) if l['lineId'] == lid) for lid in occurrence['lines']]
        if not positions or positions != list(range(positions[0], positions[0] + len(positions))):
            raise ValueError('missing_duplicate_or_noncontiguous_line')
        snapshots.append({'pieceId': v['pieceId'], 'versionId': v['versionId'], 'sourceFingerprint': v['sourceFingerprint'], 'lines': selected})
        for i, l in enumerate(selected):
            lines.append({'lineId': f'composite-{si}-{i}', 'text': transform_case(l['text'], mode),
                          'breakBefore': i == 0 and si > 0, 'sourceLineId': l['lineId'],
                          'sourceVersionId': v['versionId'], 'partId': step['partId'], 'occurrence': step['occurrence']})
        for exposure in v.get('exposures', []):
            if exposure not in exposures:
                exposures.append(deepcopy(exposure))
    return {'lines': lines, 'text': '\n'.join(('\n' if l['breakBefore'] else '') + l['text'] for l in lines),
            'sourceSnapshots': snapshots, 'verified': all(l.get('verified') is True for s in snapshots for l in s['lines']),
            'exposures': exposures}


def assemble_effective_source(source, db, pieces):
    effective = deepcopy(source)
    records = [r for r in db.get('composites', {}).values() if r.get('family') == 'composite' and r.get('pieceId') in pieces]
    for promotion in db.get('composites', {}).values():
        if promotion.get('family') != 'promotion' or promotion.get('pieceId') not in pieces:
            continue
        original = db['composites'].get(promotion.get('originComposite', {}).get('revisionId'))
        if not original or original.get('family') != 'composite':
            raise ValueError('promotion_source_missing')
        if any(p['id'] == promotion['pieceId'] for p in effective['j']['pieces']):
            raise ValueError('promotion_piece_collision')
        effective['j']['pieces'].append({'id': promotion['pieceId'], 'V': [], 'st': [], 'top': 0})
        records.append({**deepcopy(original), 'pieceId': promotion['pieceId'], 'versionId': promotion['pieceId'] + '-' + original['versionId']})
    if not any(s['pieceId'] in pieces for s in source.get('variorumSupplement', {}).get('sources', [])) and not records and not any(r.get('family') == 'parts' and r.get('pieceId') in pieces for r in db.get('parts', {}).values()):
        return effective
    versions = catalog(source, db)
    for piece in effective['j']['pieces']:
        if piece['id'] not in pieces:
            continue
        head = db.get('parts', {}).get('h.' + piece['id'], {})
        origin = next((r for r in records if r['pieceId'] == piece['id']), {})
        parts = db.get('parts', {}).get(head.get('revisionId')) or db.get('parts', {}).get(origin.get('partsRevisionId'))
        if parts:
            piece['variorum'] = deepcopy(parts)
        for src in source.get('variorumSupplement', {}).get('sources', []):
            if src['pieceId'] != piece['id']:
                continue
            imported = versions[src['versionId']]
            if any(v['id'] == src['versionId'] for v in piece['V']):
                raise ValueError('invalid_supplemental_version')
            lines = [{'lineId': src['versionId'] + '-L' + str(i+1), 'text': l['text'], 'breakBefore': l['breakBefore']} for i, l in enumerate(imported['lines'])]
            piece['V'].append({'id': src['versionId'], 'P': [], 'render': 'typeset', 'lines': lines,
                '_lineIdMap': {l['lineId']: lines[i]['lineId'] for i, l in enumerate(imported['lines'])},
                'text': '\n'.join(('\n' if l['breakBefore'] else '') + l['text'] for l in lines),
                'compositeEvidence': {'error': None if imported['available'] else 'source_unavailable',
                    'verified': bool(imported['lines']) and all(l.get('verified') is True for l in imported['lines']),
                    'sourcePieces': [src['pieceId']], 'exposures': imported.get('exposures', [])}})
            piece['st'].append(len(piece['V'])-1)
        for record in (r for r in records if r['pieceId'] == piece['id']):
            mapping = db.get('parts', {}).get(record['partsRevisionId'])
            resolved, error = None, None
            try:
                resolved = materialize(versions, mapping, record['recipe'], record['caseMode'])
                if canonical(resolved['sourceSnapshots']) != canonical(record['sourceSnapshots']) or resolved['text'] != record['text'] or canonical(resolved['lines']) != canonical(record['lines']):
                    raise ValueError('stale_composite_source')
            except (ValueError, KeyError) as exc:
                error = str(exc)
            if record.get('render') not in ('typeset', 'photo'):
                error = 'invalid_composite_render'
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', record['versionId']) or any(x['id'] == record['versionId'] for x in piece['V']):
                raise ValueError('duplicate_or_invalid_version')
            lines = [{'lineId': record['versionId'] + '-L' + str(i + 1), 'text': l['text'], 'breakBefore': l['breakBefore']} for i, l in enumerate(record.get('lines', []))]
            v = {'id': record['versionId'], 'P': [], 'render': record['render'], 'lines': lines, 'text': record['text'],
                 'compositeRevision': record['revisionId'], 'compositeEvidence': {'error': error, 'verified': bool(resolved and resolved['verified']),
                 'sourcePieces': [s['pieceId'] for s in record.get('sourceSnapshots', [])], 'exposures': resolved['exposures'] if resolved else []}}
            if record.get('photo'):
                v['photo'] = {'url': 'img/p/' + record['versionId'] + '.jpg'}
                v['compositeEvidence']['photo'] = deepcopy(record['photo'])
            if 'variorum' in piece and mapping:
                segments, order, offset = {}, [], 0
                for step in record['recipe']:
                    key = step['partId']
                    occ = next((o for o in mapping['maps'].get(step['from'], {}).get('segments', {}).get(key, []) if o['occurrence'] == step['occurrence']), {})
                    count = len(occ.get('lines', []))
                    if not any(p['id'] == key for p in piece['variorum']['parts']):
                        part = next((p for p in mapping['parts'] if p['id'] == key), None)
                        if part:
                            piece['variorum']['parts'].append(deepcopy(part)); piece['variorum']['canonicalOrder'].append(key)
                    occurrence = step['occurrence']
                    segments.setdefault(key, []).append({'occurrence': occurrence, 'lines': [l['lineId'] for l in lines[offset:offset+count]], 'accepted': True})
                    order.append({'partId': key, 'occurrence': occurrence}); offset += count
                piece['variorum']['maps'][record['versionId']] = {'segments': segments, 'version_part_order': order}
            piece['V'].append(v); piece['st'].append(len(piece['V']) - 1)
    return effective


def public_version(v):
    return {k: deepcopy(x) for k, x in v.items() if k not in ('compositeEvidence', 'compositeRevision', '_lineIdMap')}


def project_public_variorum(record, visible_versions):
    ids = {v['id'] for v in visible_versions}
    maps = {}
    for key, mapping in record.get('maps', {}).items():
        if key not in ids:
            continue
        remap = next(v for v in visible_versions if v['id'] == key).get('_lineIdMap', {})
        segments = {part: [{'occurrence': o['occurrence'], 'lines': [remap.get(lid, lid) for lid in o['lines']]} for o in occurrences if o.get('accepted')]
                    for part, occurrences in mapping.get('segments', {}).items()}
        maps[key] = {'segments': segments, 'version_part_order': [o for o in mapping.get('version_part_order', []) if any(x['occurrence'] == o['occurrence'] for x in segments.get(o['partId'], []))]}
    used = {part for m in maps.values() for part in m['segments']}
    return {'parts': [{'id': p['id'], 'name': p.get('name')} for p in record['parts'] if p['id'] in used], 'canonicalOrder': [p for p in record['canonicalOrder'] if p in used], 'maps': maps}


def check_composite(v, source, db, target='production'):
    evidence = v.get('compositeEvidence')
    if not evidence:
        return
    if evidence['error']:
        raise ValueError(evidence['error'])
    if evidence['verified'] is not True:
        raise ValueError('unverified_composite')
    if any(db.get('release', {}).get(p, {}).get('pool') in ('reserve', 'archive') for p in evidence['sourcePieces']):
        raise ValueError('source_pool_withheld')
    if v['render'] == 'typeset' and target != 'staging':
        font = source.get('variorumFontEvidence', {})
        if font.get('approved') is not True or font.get('coversShellSha256') != source.get('shellSha256') or not font.get('approvalRef') or any(ord(c) not in font.get('codepoints', []) for c in v['text'] if not c.isspace()):
            raise ValueError('composite_glyph_evidence_missing')
    if v['render'] == 'photo':
        photo = evidence.get('photo', {})
        if not re.fullmatch('[a-f0-9]{64}', photo.get('sha256', '')) or type(photo.get('size')) is not int:
            raise ValueError('composite_photo_evidence_missing')
