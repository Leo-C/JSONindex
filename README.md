# JSON indexer

## Description

**JSON indexer** is a python-3 mini-library useful to index portions of huge JSONs, if we want access only parts of entire JSON.

These portions can be only JSON objects (between `{}`) or JSON array (between `[]`)



## Installation

Only action requested is copy `JSONindex.py` module into own project. 



## Use

The module expose 2 items:

* a function `buildJSONindex()`, useful to extract references to desired sub-parts of JSON
* a class `SubStream`, useful to access sub-parts of huge JSONs
  
  
### buildJSONindex()
The function `buildJSONindex()` accept 4 arguments:

* _input stream_: a stream that contains a JSON (file, string, socket, etc.)
* _output stream_: is filled with minified copy of input JSON
* _static prefixes_ (optional): a list of prefixes pointing to sub-objects or sub-array of the input JSON to extract
* _regexp prefixes_ (optional): a list of regular expression to match sub-objects or sub-array of the input JSON to extract

and return an index of sub-objects or sub-array relative to minified JSON produced
  
  
  
*[Prefixes](https://github.com/ICRAR/ijson#id2)* are expressed as required by [ijson SAX parser](https://pypi.org/project/ijson/) (used in `buildJSONindex()`)

Index is a dictionary with following structure:
```
index = {"prefix#1" -> (pos_start_#1, pos_end_#1), 
         "prefix#2" -> (pos_start_#2, pos_end_#2), 
		 ... }
```
with:

* _pos_start_: first byte (0-based) of sub-section
* _pos_end_: 1st byte after last byte of sub-section
  
  
### SubStream

After getting index, we can use `SubStream` to access sub-section of interest.

Constructor simply require underlying _stream_ (buffered or not), and _start_ and _end_ positions of sub-section obtained by `buildJSONindex()`:
```
substream = SubStream(stream, pos_start, pos_end)
```
  
This substream can be transparently used with any json parser (e.g. python standard [`json.load()`](https://docs.python.org/3/library/json.html#json.load), or any DOM or SAX parser), jumping in constant time to specified sub-section (if underlying stream support `seek()`; otherwise desired sub-section is accessed in linear time, but faster than using JSON parser).  



## Appendix

### Requirements

[ijson](https://pypi.org/project/ijson/) (developed & tested with version 3.1.3)


### Test & Performance

A file `tests.py` for unit testing of two modules is included in distribution.
It contains also a performance test.

Tests can be run with:
```
python -m unittest tests
```
(only unit tests)

or with:
```
python -m tests <basename> <prefix>
```
(both unit tests and performance test are run)
where:

* `<basename>` is base of json file for performance test
  * `<basename>.json` is input json file
  * `<basename>_min.json` is minified output json file
  * `<basename>_idx.json` is JSON dump of index
* `<prefix>` is prefix searched into input JSON



As example for a 800 MB JSON with structure:
```
{'a': [{<5-field object>} ... (250k objects)],
 'b': (same as above),
 ...
 'd': (same as above) }
```
it scan and minify JSON with following results (using Win10 64-bit on a Ryzen7 @3.8 GHz with NVMe SSD):

* **time**: run in about 260-270 sec (about 3.5 MB / sec)
* **size**: -11% for minified file
* **RAM**: requiring constantly 10-15 MB of RAM (depending on python interpreter)



### License

This library (and related sources) is subject to [MIT license](https://opensource.org/licenses/MIT). 
Any commercial use **should be** (as specified in [RFC 2119](https://tools.ietf.org/html/rfc2119)) notified to author.
