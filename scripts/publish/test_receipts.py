"""Offline receipt regressions: python3 -m unittest discover -s scripts/publish -p 'test_*.py'."""
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location('publisher', HERE / 'publish_gguf.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = 'LFM3-VL-2B-MobileAgent-Dev-FullMix'
        self.repo = 'experimentalmachines/' + self.base
        self.rev = 'a' * 40
        self.weights = self.root / 'model.safetensors'
        self.weights.write_bytes(b'converted source weights')
        self.hashes = {self.weights.name: hashlib.sha256(self.weights.read_bytes()).hexdigest()}
        self.info = NS(sha=self.rev, siblings=[NS(rfilename=n, lfs=NS(sha256=h)) for n, h in self.hashes.items()])
        self.gguf = self.root / (self.base + '-Q4_K_M.gguf')
        self.gguf.write_bytes(b'fake gguf')
        self.receipt = {'source_repo': self.repo, 'source_revision': self.rev, 'source_files_sha256': self.hashes,
                        'quantization': 'Q4_K_M', 'output_sha256': publisher.sha256(self.gguf), 'llama_cpp_commit': 'cd959bae9'}

    def test_generator_resolves_branch_to_commit(self):
        args = ['make_receipt.py', self.repo, str(self.gguf), 'Q4_K_M', '--input-dir', str(self.root), '--revision', 'main']
        with patch.object(sys, 'argv', args), patch('huggingface_hub.HfApi') as api, patch('subprocess.run', return_value=NS(stdout='cd959bae9')):
            api.return_value.model_info.return_value = self.info
            runpy.run_path(str(HERE / 'make_receipt.py'), run_name='__main__')
        receipt = json.loads(Path(str(self.gguf) + '.receipt.json').read_text())
        self.assertEqual(receipt['source_revision'], self.rev)
        self.assertEqual(receipt['source_files_sha256'], self.hashes)

    def publish(self, info=None, parity=False, compare_status=0):
        Path(str(self.gguf) + '.receipt.json').write_text(json.dumps(self.receipt))
        (self.root / 'cards' / 'models').mkdir(parents=True, exist_ok=True)
        projector = self.root / 'projector.gguf'
        projector.write_bytes(b'projector')
        reader = NS(fields={'general.file_type': NS(contents=lambda: 15)}, tensors=[None] * 287)
        args = ['publish_gguf.py', 'FullMix', str(self.gguf)]
        if parity:
            args += ['--parity', 'earlier.gguf']
        with patch.object(sys, 'argv', args), patch.object(publisher, 'HERE', str(self.root)), \
             patch.object(publisher, 'MMPROJ', str(projector)), patch.object(publisher, 'MMPROJ_SHA', publisher.sha256(projector)), \
             patch.object(publisher, 'HfApi') as api, patch.dict(sys.modules, {'gguf': NS(GGUFReader=lambda _: reader)}), \
             patch.object(publisher.subprocess, 'run', return_value=NS(returncode=compare_status, stdout='names equal True\ntensors differing: 0', stderr='failed after output')):
            api.return_value.model_info.return_value = info or self.info
            publisher.main()
            return api.return_value.model_info.call_args_list

    def test_publisher_checks_pinned_and_current_weights(self):
        calls = self.publish()
        self.assertEqual(calls[0].kwargs['revision'], self.rev)
        self.assertNotIn('revision', calls[1].kwargs)

    def test_publisher_rejects_mutable_revision(self):
        self.receipt['source_revision'] = 'main'
        with self.assertRaisesRegex(AssertionError, 'immutable'):
            self.publish()

    def test_publisher_rejects_wrong_pinned_weights(self):
        self.receipt['source_files_sha256'] = {'model.safetensors': 'wrong'}
        with self.assertRaisesRegex(AssertionError, 'pinned source'):
            self.publish()

    def test_publisher_rejects_comparison_that_fails_after_printing(self):
        with self.assertRaisesRegex(AssertionError, 'failed after output'):
            self.publish(parity=True, compare_status=1)

    def test_publisher_requires_opt_in_for_retrospective_receipts(self):
        self.receipt['after_the_fact'] = True
        with self.assertRaisesRegex(AssertionError, 'weaker guarantee'):
            self.publish()


if __name__ == '__main__':
    unittest.main()
