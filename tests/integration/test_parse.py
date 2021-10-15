import datetime
import os.path
import pytest

import libsgfdata as sgf

basepath = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "examples", "data")

class TestParse:
    def test_parse(self):
        for name in os.listdir(basepath):
            d = sgf.parse(os.path.join(basepath, name))

    def test_write(self):
        for name in os.listdir(basepath):
            d = sgf.parse(os.path.join(basepath, name))
            sgf.dump(d, "tmp.sgf")

    def test_write_read(self):
        for name in os.listdir(basepath):
            orig = sgf.parse(os.path.join(basepath, name))
            sgf.dump(orig, "tmp.sgf")
            reread = sgf.parse("tmp.sgf")
            assert len(reread) == len(orig)
            for idx, (orig_section, reread_section) in enumerate(zip(orig, reread)):
                assert list(orig_section.keys()) == list(reread_section.keys()), "%s: %s" % (name, idx)
                for blockname in orig_section.keys():
                    orig_block = orig_section[blockname]
                    reread_block = reread_section[blockname]
                    assert len(orig_block) == len(reread_block), "%s: %s: %s" % (name, idx, blockname)
                    if hasattr(orig_block, "columns"):
                        assert (orig_block.columns == reread_block.columns).all(), "%s: %s: %s" % (name, idx, blockname)
                    elif hasattr(orig_block, "keys"):
                        assert list(orig_block.keys()) == list(reread_block.keys()), "%s: %s: %s" % (name, idx, blockname)
