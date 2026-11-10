"""Regression: preparation must atomically refresh the canonical mask bundle."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


class SourceBundleTest(unittest.TestCase):
    def test_preparation_writes_scene_and_both_masks_to_packager_input(self):
        spec=importlib.util.spec_from_file_location('prepare_source',ROOT/'tools/prepare_source.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as folder:
            mod.ROOT=Path(folder)
            source=ROOT/'data/source/ferry.json'
            with patch.object(sys,'argv',['prepare_source.py','--source',str(source)]):mod.main()
            bundle=mod.ROOT/'data/source'
            for name in ['scene.json','depth.png','water.png']:
                self.assertTrue((bundle/name).is_file(),f'Canonical {name} was not regenerated')
            scene=json.loads((bundle/'scene.json').read_text())
            for name in ['depth','water']:
                with Image.open(bundle/f'{name}.png') as image:self.assertEqual(image.size,(scene['width'],scene['height']))


if __name__=='__main__':unittest.main()
