import ast
import re
from pathlib import Path


def test_all_docs_python_blocks_are_valid_python():
    errors = []
    block_count = 0

    for path in (Path(__file__).parents[2] / 'docs').rglob('*.md'):
        if 'api_reference' in path.parts or 'oauth' in path.parts:
            continue

        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = path.read_text(encoding='utf-8', errors='replace')

        blocks = re.findall(r'```python\s*\n(.*?)```', text, flags=re.DOTALL)

        for block_number, block in enumerate(blocks, start=1):
            block_count += 1
            try:
                ast.parse(block)
            except SyntaxError as exc:
                errors.append(f'{path} block {block_number}: {exc.msg} at line {exc.lineno}')

    assert block_count > 0
    assert errors == [], '\n'.join(errors)
