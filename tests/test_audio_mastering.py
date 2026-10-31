import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "audio_mastering.py"
spec = importlib.util.spec_from_file_location("audio_mastering", SOURCE)
audio_mastering = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audio_mastering)


class AudioMasteringTests(unittest.TestCase):
    def test_mono_input_uses_dual_mono_and_stereo_does_not(self):
        common = dict(target_lufs=-16, true_peak=-1.5, lra=11)
        mono = audio_mastering.build_filter_chain(channels=1, **common)
        stereo = audio_mastering.build_filter_chain(channels=2, **common)
        self.assertIn("dual_mono=true", mono)
        self.assertIn("dual_mono=false", stereo)

    def test_speech_processing_is_opt_in_and_ends_before_loudness_measurement(self):
        chain = audio_mastering.build_filter_chain(
            channels=2,
            target_lufs=-16,
            true_peak=-1.5,
            lra=11,
            post_filters="afade=t=out:st=60:d=0.5,apad=pad_dur=2",
            speech_cleanup=True,
        )
        self.assertLess(chain.index("highpass=f=80"), chain.index("loudnorm="))
        self.assertLess(chain.index("deesser=i=0.4"), chain.index("loudnorm="))
        self.assertLess(chain.index("acompressor="), chain.index("loudnorm="))
        self.assertLess(chain.index("apad=pad_dur=2"), chain.index("loudnorm="))

    def test_parses_ffmpeg_loudnorm_output_after_log_text(self):
        logs = '''ffmpeg diagnostic\n{\n"input_i": "-17.2",\n"input_tp": "-2.1",\n"input_lra": "4.0",\n"input_thresh": "-27.4",\n"target_offset": "1.2"\n}\n'''
        result = audio_mastering.parse_loudnorm_stats(logs)
        self.assertEqual(result["input_i"], "-17.2")
        self.assertEqual(result["target_offset"], "1.2")


if __name__ == "__main__":
    unittest.main()
