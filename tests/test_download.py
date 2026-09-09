import runpy
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock


APP = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'baixatudo.pyw'))
GLOBALS = APP['find_ffmpeg'].__globals__


class DownloadTests(unittest.TestCase):
    def test_requires_both_tools_and_searches_nested_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.dict(GLOBALS, TOOLS_DIR=root, APP_ROOT=root, BUNDLE_ROOT=root), patch('shutil.which', return_value=None):
                (root / 'ffmpeg.exe').touch()
                self.assertIsNone(APP['find_ffmpeg']())
                nested = root / 'ffmpeg' / 'bin'
                nested.mkdir(parents=True)
                for name in ('ffmpeg.exe', 'ffprobe.exe'):
                    (nested / name).touch()
                self.assertEqual(APP['find_ffmpeg'](), str(nested))

    def test_passes_tool_directory_as_single_argument(self):
        app = APP['BaixatudoApp'].__new__(APP['BaixatudoApp'])
        app._send = MagicMock()
        app.stop_event = threading.Event()
        app.process_lock = threading.Lock()
        process = MagicMock()
        process.stdout = []
        process.wait.return_value = 0
        with patch.dict(GLOBALS, find_ffmpeg=lambda: 'C:/tools with spaces'), patch('subprocess.Popen', return_value=process) as popen:
            self.assertEqual(app._run_yt_dlp('yt-dlp', 'https://youtu.be/example', Path('.'), 'Somente audio MP3', False, True), 0)
        args = popen.call_args.args[0]
        self.assertEqual(args[args.index('--ffmpeg-location') + 1], 'C:/tools with spaces')
        self.assertIn('--audio-format', args)

    def test_failed_dependency_install_prevents_download(self):
        app = APP['BaixatudoApp'].__new__(APP['BaixatudoApp'])
        app._send = MagicMock()
        app._run_yt_dlp = MagicMock()
        app.stop_event = threading.Event()
        app.process_lock = threading.Lock()
        with tempfile.TemporaryDirectory() as temporary, patch.dict(GLOBALS, ensure_ffmpeg=MagicMock(side_effect=RuntimeError('network failed'))):
            app._download_worker('yt-dlp', ['https://youtu.be/example'], Path(temporary), 'Somente audio MP3', False, True)
        app._run_yt_dlp.assert_not_called()
        app._send.assert_any_call('log', 'Erro: network failed')


if __name__ == '__main__':
    unittest.main()
