import io
import os
import sys
import time
import json
import unittest

from JSONindex import SubStream, buildJSONindex


class TestStream(unittest.TestCase):
    def setUp(self):
        self._f = open("test.json", "r")
        self._s = SubStream(self._f, 253, 790) # entire object 'geometry'
        self.reset()
    
    def reset(self):
        self._f.seek(0)
        self._s.seek(0)
    
    def test_seek(self):
        self._s.seek(0)
        self._s.seek(3)
        self.assertEqual(self._f.tell(), 256)
        self._s.seek(3, 1)
        self.assertEqual(self._f.tell(), 259)
        self._s.seek(-3, 2)
        self.assertEqual(self._f.tell(), 787)
    
    def test_readline(self):
        self.reset()
        self._s.readline()
        line = self._s.readline() #2nd line
        self.assertEqual(line, "    \"type\": \"Polygon\",\n")
    
    def test_readlines(self):
        self.reset()
        lines = self._s.readlines()
        self.assertEqual(lines[-1], "  }")
    
    def test_read(self):
        self._s.seek(532) #set to last ']'
        buf = self._s.read(10)
        self.assertEqual(buf, "]\n  }")
        
        self._s.seek(532)
        buf = self._s.read(4) #set to last ']'
        self.assertEqual(buf, "]\n  ")
    
    def test_readinto(self):
        buf = bytearray(10)
        self._s.seek(532) #set to last ']'
        n = self._s.readinto(buf)
        self.assertEqual(n, 5)
        self.assertEqual(buf[0:n], b"]\n  }")
        
        buf = bytearray(4)
        self._s.seek(532)
        n = self._s.readinto(buf) #set to last ']'
        self.assertEqual(n, 4)
        self.assertEqual(buf, b"]\n  ")
    
    def test_closed(self):
        self.reset()
        self.assertFalse(self._s.closed)
    
    def test_writes(self):
        self.reset()
        with self.assertRaises(io.UnsupportedOperation):
            self._s.flush()
        with self.assertRaises(io.UnsupportedOperation):
            self._s.truncate(3)
        with self.assertRaises(io.UnsupportedOperation):
            self._s.write("")
        with self.assertRaises(io.UnsupportedOperation):
            self._s.writelines([])
    
    def test_substream(self):
        self.reset()
        sub_json = json.load(self._s) #check if sub-JSON is consistent
        check_dict = {"type": "Polygon",
                      "coordinates": [ [ [ -122.42200352825247, 37.80848009696725, 0 ],
                                         [ -122.42207601332528, 37.808835019815085, 0 ],
                                         [ -122.42110217434863, 37.808803534992904, 0 ],
                                         [ -122.42106256906727, 37.80860105681815, 0 ],
                                         [ -122.42200352825247, 37.80848009696725, 0 ] ] ] }
        self.assertDictEqual(sub_json, check_dict)
    
    def tearDown(self):
        self._f.close()


class TestJSONindex(unittest.TestCase):
    def setUp(self):
        self._in = open("test.json", "rb")
        self._out = None
    
    def reset(self):
        self._in.seek(0)
        if self._out != None:
            if not self._out.closed:
                self._out.close()
        self._out = open("test_out.json", "wb+")
        
    def test_build_index_all(self):
        _in = io.BytesIO(b"{ }")
        _out = io.BytesIO()
        idx = [""]
        index = buildJSONindex(_in, _out, idx)
        self.assertDictEqual(index, {"": {"start": 0, "end": 2}})
        self.assertEqual(b"{}", _out.getvalue())
    
    def test_sub_json(self):
        self.reset()
        idx = ["geometry.coordinates"]
        index = buildJSONindex(self._in, self._out, idx)
        self._out.close()
        self._in.seek(0)
        json_in = json.load(self._in)
        
        #load a sub-JSON
        start = index["geometry.coordinates"]["start"]
        end = index["geometry.coordinates"]["end"]
        self._out = open("test_out.json", "rb")
        sub_stream = SubStream(self._out, start, end)
        sub_json = json.load(sub_stream)
        self._out.close()
        self.assertCountEqual(json_in["geometry"]["coordinates"], sub_json)
    
    def test_minify_json(self):
        self.reset()
        idx = []
        re_idx = []
        index = buildJSONindex(self._in, self._out, idx, re_idx)
        self._out.close()
        
        f1 = open("test.json", "r")
        json_orig = json.load(f1)
        f1.close()
        f2 = open("test_out.json", "r")
        json_minified = json.load(f2)
        f2.close()
        self.assertDictEqual(json_orig, json_minified)
    
    def test_build_index_static(self):
        self.reset()
        idx = ["geometry.coordinates"]
        index = buildJSONindex(self._in, self._out, idx)
        self.assertDictEqual(index, {"geometry.coordinates": {"start": 216, "end": 431}})
    
    def test_build_index_regexp(self):
        self.reset()
        re_idx = ["geometry\.[^\.]+"] #match only 'geometry.coordinates' and not 'geometry.item*'
        index = buildJSONindex(self._in, self._out, regexp_prefixes = re_idx)
        self.assertDictEqual(index, {"geometry.coordinates": {"start": 216, "end": 431}})
    
    def tearDown(self):
        if (self._in != None):
            self._in.close()
            self._in = None
        if (self._out != None):
            self._out.close()
            self._out = None


def test_performance(basename, prefix):
    # define prefixes for indexing
    idx = [prefix]
    re_idx = []
    
    fname_in = basename+".json"
    fname_out = basename+"_min.json"
    json_in = io.BufferedReader(open(fname_in, "rb"), 128*1024) #128kB of read buffer
    json_min = io.BufferedWriter(open(fname_out, "wb+"), 128*1024) #128kB of write buffer
    json_index = open(basename+"_idx.json", "w")
    
    before = time.time()
    index = buildJSONindex(json_in, json_min, idx, re_idx)
    after = time.time()
    json.dump(index, json_index, indent=4)
    
    json_index.close()
    json_min.close()
    json_in.close()
    
    #print some statistics
    size_in = os.stat(fname_in).st_size
    size_out = os.stat(fname_out).st_size
    print("Original file size: %d bytes" % size_in)
    print("Minified file size: %d bytes (%d%%)" % (size_out, round(100*(size_out - size_in)/size_in, 0)))
    print("Elapsed time: %.3f ms" % (1000*(after-before)))


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        prefix = sys.argv.pop()
        basename = sys.argv.pop()
        test_performance(basename, prefix)
        print()
    else:
        print("Usage: python -m tests <basename> <prefix>")
        print("  where:")
        print("  - <basename>.json is test file")
        print("      (<basename>_min.json is file minified)")
        print("      (<basename>_idx.json is index dump)")
        print("  - <prefix> is searched prefix")
        print()
    
    unittest.main()
